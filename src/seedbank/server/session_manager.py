#
# Copyright 2012 ibiblio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import multiprocessing
import threading
import time
from Queue import Empty
import terasaur.log.log_helper as log_helper
from terasaur.config.config_helper import MAIN_SECTION, MONGODB_SECTION
from seedbank.config.config_defaults import UPLOAD_SECTION
from seedbank.server.libtorrent_session import LibtorrentServerSession, LibtorrentClientSession, LibtorrentSessionQueueItem
import seedbank.server.alert_match as alert_match
from terasaur.db.torrent_db import TORRENT_COLLECTION
from terasaur.mixin.timestamp import TimestampMixin

# Synchronization is cleaner when implemented at the module level
# with a decorator.  The only caveat is that we can only have one
# session manager.
_SESSION_LOCK = threading.Semaphore()

def threading_guard(func):
    """
    Acquire _SESSION_LOCK.  Implement a 1 sec timeout; don't
    block and risk deadlock.
    """
    def _wrap(*args, **kwargs):
        try:
            locked = False
            count = 0
            stop = 10
            # Fail, don't deadlock
            while locked is False and count < stop:
                locked = _SESSION_LOCK.acquire(False)
                time.sleep(0.1)
                count += 1
            if not locked:

                raise Exception('Unable to acquire session manager lock')
            return func(*args, **kwargs)
        finally:
            _SESSION_LOCK.release()
    return _wrap

class SessionManagerException(Exception): pass

# TODO: do we really need threading guards on instances?
class SessionInstance(TimestampMixin):
    def __init__(self, params):
        """
        In and out are from the perspective of the LibtorrentSession process
            * in_q sends messages to the session process
            * out_q receives messages
        """
        self.in_q = multiprocessing.Queue()
        self.out_q = multiprocessing.Queue()
        self._queue_timeout = 0.5
        self._key = params['key']
        self._session_type = params['session_type']
        self._torrent_count = 0
        self._stop_sent = False
        self.__init_session_process(params)

    def __init_session_process(self, params):
        params['in_queue'] = self.in_q
        params['out_queue'] = self.out_q
        if self.is_server():
            self.proc = LibtorrentServerSession(**params)
        else:
            self.proc = LibtorrentClientSession(**params)

    def start(self):
        self._started = self._get_now()
        self.proc.start()

    def stop(self):
        if self.in_q and not self._stop_sent:
            self.in_q.put(LibtorrentSessionQueueItem('stop', True))
            self._stop_sent = True

    def check_queue(self):
        item = None
        try:
            item = self.out_q.get(block=True, timeout=self._queue_timeout)
        except Empty:
            pass
        except IOError:
            # Occurs when a SIGTERM is received while waiting in queue.get()
            pass

        # intercept updates for the session manager
        if item and item.type == 'update':
            self._handle_update(item)
            item = None
        return item

    def _handle_update(self, item):
        self._torrent_count = item.value['torrent_count']

    def is_server(self):
        return self._session_type == 'server'

    def has_active_torrents(self):
        return self._torrent_count > 0

    def age(self):
        """
        Returns number of seconds since the instance was started
        """
        return self._seconds_since(self._started)

    def is_stopping(self):
        return self._stop_sent

class SessionManager(object):
    """
    Coordinates multiple forked processes with libtorrent sessions.  Each
    process has in and out queues for communication.
    """
    CLEANUP_MIN_AGE = 30

    def __init__(self, **kwargs):
        self._sessions = {}
        self._log = log_helper.get_logger(self.__class__.__name__)
        self._verbose = kwargs.get('verbose', False)
        self._debug = kwargs.get('debug', False)
        self._config = kwargs.get('config', None)
        self._run = True

    @threading_guard
    def create(self, key, **kwargs):
        if self._sessions.has_key(key):
            raise SessionManagerException('Session manager key already in use')
        self._sessions[key] = self._create_session(key, **kwargs)

    def _create_session(self, key, **kwargs):
        s_type = kwargs.get('session_type', None)
        if s_type == 'server':
            params = self._get_server_params(**kwargs)
        else:
            params = self._get_client_params(**kwargs)
        params['key'] = key
        self._log.info('Creating new session instance: %s' % key)
        session = SessionInstance(params)
        session.start()
        return session

    def send(self, key, item):
        """
        Put a LibtorrentSessionQueueItem in the inbound queue for the given
        session instance key.
        """
        if self._sessions.has_key(key):
            self._sessions[key].in_q.put(item)
        else:
            self._log.error('Cannot send message to a process that does not exist (%s)' % key)

    def stop(self, key=None):
        """
        Stop a session instance for the given key.  If no key is provided, stop
        all session instances.
        """
        if key:
            self._stop(key)
        else:
            # Trigger an all-stop, see tick()
            self._run = False

    def _stop(self, key):
        if self._sessions.has_key(key):
            self._sessions[key].stop()
        else:
            self._log.error('Cannot stop a process that does not exist (%s)' % key)

    def is_alive(self, key):
        return self._sessions.has_key(key) and self._sessions[key].proc.is_alive()

    def join(self, key=None):
        """
        Force join on a session process.  If no key is specified, wait for all
        sessions to end.  The latter should only be performed during the shutdown
        sequence in SeedbankServer.
        """
        if key:
            self._join(key)
        else:
            self._join_all()

    def _join(self, key):
        if self._sessions.has_key(key):
            if self._debug:
                self._log.info('Waiting for LibtorrentSession process to stop (key: %s)' % key)
            self._sessions[key].proc.join()
        else:
            self._log.error('Cannot join a process that does not exist (%s)' % key)

    def _join_all(self):
        for key in self._sessions.keys():
            self._join(key)

    def tick(self):
        """
        For asynchronous tasks.  This should only be called from the main
        SeedbankServer run loop.
        """
        if not self._run:
            self._stop_all()
        self._cleanup()

    @threading_guard
    def _stop_all(self):
        """
        Send stop signal to all sessions.
        """
        for key in self._sessions.keys():
            self._sessions[key].stop()

    @threading_guard
    def _cleanup(self):
        """
        Perform cleanup tasks on session instances
        """
        for key in self._sessions.keys():
            instance = self._sessions[key]

            # Destroy processes that have finished
            if not instance.proc.is_alive():
                self._log.info('Cleaning up stopped session %s' % key)
                instance.proc.join()
                del self._sessions[key]

            # Remove sessions that have no torrents
            if self._should_stop_instance(instance):
                self._log.info('Stopping session %s due to lack of active torrents' % key)
                instance.stop()

    def _should_stop_instance(self, instance):
        if not instance.is_server() \
                and not instance.is_stopping() \
                and not instance.has_active_torrents() \
                and not instance.age() < SessionManager.CLEANUP_MIN_AGE:
            return True
        else:
            return False

    @threading_guard
    def check_queues(self):
        items = []
        for key, instance in self._sessions.iteritems():
            item = instance.check_queue()
            if item:
                if self._verbose:
                    self._log.info('Got item from queue (%s):' % key)
                    self._log.info('%s: %s' % (item.type, item.value))
                items.append(item)
        return items

    def _get_client_params(self, **kwargs):
        params = self._get_general_params(**kwargs)
        config = kwargs.get('config', None)
        client_alerts = self._get_client_alert_match_list(config)
        params['watcher_match_list'] = client_alerts
        params['listen_min'] = config.getint(UPLOAD_SECTION, 'upload_port_min')
        params['listen_max'] = config.getint(UPLOAD_SECTION, 'upload_port_min')
        params['inactive_torrent_timeout'] = config.getint(UPLOAD_SECTION, 'torrent_timeout')
        return params

    def _get_server_params(self, **kwargs):
        params = self._get_general_params(**kwargs)
        config = kwargs.get('config', None)
        mongodb_plugin_params = self._get_mongodb_plugin_params(config)
        server_alerts = self._get_server_alert_match_list(config)
        params['listen_min'] = config.getint(MAIN_SECTION, 'listen_port')
        params['listen_max'] = config.getint(MAIN_SECTION, 'listen_port')
        params['mongodb_plugin_params'] = mongodb_plugin_params
        params['watcher_match_list'] = server_alerts
        return params

    def _get_general_params(self, **kwargs):
        config = kwargs.get('config', None)
        tick_interval = kwargs.get('tick_interval', None)
        params = {
            'verbose': self._verbose,
            #'peer_id': PEER_ID,
            'tick_interval': tick_interval,
            'watcher_loop_limit': 0, # watcher should never exit
            'stop_on_watcher_exit': False,
            'inactive_torrent_timeout': config.getint(MAIN_SECTION, 'inactive_torrent_timeout'),
            'torrent_manager_exec_interval': config.getint(MAIN_SECTION, 'torrent_manager_exec_interval'),
            'session_type': kwargs.get('session_type', 'client')
            }
        return params

    def _get_mongodb_plugin_params(self, config):
        db_host = config.get(MONGODB_SECTION, 'db_host')
        db_port = config.getint(MONGODB_SECTION, 'db_port')
        db_name = config.get(MONGODB_SECTION, 'db_name')
        torrent_file_root = config.get(MAIN_SECTION, 'torrent_file_root')

        params = {
            'connection_string': db_host + ':' + str(db_port),
            'torrentdb_ns': db_name + '.' + TORRENT_COLLECTION,
            'torrent_file_root': torrent_file_root}
        return params

    def _get_server_alert_match_list(self, config):
        alerts = self._get_client_alert_match_list(config)
        alerts.append(('mongodb', alert_match.MongodbAlertMatch, {'expires_after': 0, 'log_on_match': True}))
        return alerts

    def _get_client_alert_match_list(self, config):
        alerts = [
            ('listen_succeeded', alert_match.ListenSucceededAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('listen_failed', alert_match.ListenFailedAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('torrent_finished', alert_match.TorrentFinishedAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('incoming_connection', alert_match.IncomingConnectionAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('peer_connect', alert_match.PeerConnectAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('peer_disconnect', alert_match.PeerDisconnectedAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('file_error', alert_match.FileErrorAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('torrent_error', alert_match.TorrentErrorAlertMatch, {'expires_after': 0, 'log_on_match': True}),
            ('tracker_error', alert_match.TrackerErrorAlertMatch, {'expires_after': 0, 'log_on_match': True})
            ]
        if self._verbose:
            alerts.append(('torrent_stats', alert_match.TorrentStatsAlertMatch, {'expires_after': 0, 'log_on_match': True}),)
        return alerts
