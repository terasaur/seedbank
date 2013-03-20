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
#@PydevCodeAnalysisIgnore
import time
import binascii
import multiprocessing

import libtorrent as lt
from seedbank.server.libtorrent_settings import get_server_settings
from seedbank.server.alert_watcher import UnthreadedAlertWatcher, ThreadedAlertWatcher
import terasaur.log.log_helper as log_helper
from seedbank.messaging.libtorrent_status import StatusPrinter, TorrentStatusPrinter
from seedbank.messaging.torrent_stats_publisher import TorrentStatsPublisher
from terasaur.messaging.rabbitmq_publisher import RabbitMQPublisher
from seedbank.messaging.server_stats_publisher import ServerStatsPublisher
from seedbank.server.torrent_manager import TorrentManager
import terasaur.config.config_helper as config_helper
from seedbank.server.session_queue_handler import ServerQueueHandler, ClientQueueHandler
from seedbank.server.session_queue_item import LibtorrentSessionQueueItem

ALERT_MASK_DEFAULT = lt.alert.category_t.all_categories | lt.alert.category_t.stats_notification
ALERT_MASK_STATS = lt.alert.category_t.all_categories

__all__ = ['LibtorrentSession', 'LibtorrentServerSession', 'LibtorrentSessionQueueItem', 'ALERT_MASK_DEFAULT', 'ALERT_MASK_STATS']

class LibtorrentSessionException(Exception): pass

class LibtorrentSession(multiprocessing.Process):
    def __init__(self, **kwargs):
        self._label = kwargs.get('key', '')
        multiprocessing.Process.__init__(self, None, self._label)
        self._status_printer = StatusPrinter(self._label)
        self._ses = None
        self._run = False
        self._log = log_helper.get_logger(self.__class__.__name__)

        self._in_q = kwargs.get('in_queue', None) # Process.Queue
        self._out_q = kwargs.get('out_queue', None) # Process.Queue
        self._queue_handler = None
        self._mongodb_plugin_params = kwargs.get('mongodb_plugin_params', None)
        self._peer_id = kwargs.get('peer_id', None)
        self._verbose = bool(kwargs.get('verbose', False))
        self._tick_interval = kwargs.get('tick_interval', 0.1)
        self._server_stats_publisher = None
        self._listen_min = int(kwargs.get('listen_min', 0))
        self._listen_max = int(kwargs.get('listen_max', 0))

        # send updates to the session manager
        self._update_counter = 0
        self._update_interval = 10 # number of ticks between updates

        # alert watcher
        self._watcher = None
        self._watcher_class = UnthreadedAlertWatcher # can override this in derived class
        self._watcher_loop_limit = int(kwargs.get('watcher_loop_limit', 250))
        self._watcher_match_list = kwargs.get('watcher_match_list', [])
        self._stop_on_watcher_exit = bool(kwargs.get('stop_on_watcher_exit', False))

        # torrent manager
        self._torrent_manager = None
        self._torrent_manager_exec_interval = kwargs.get('torrent_manager_exec_interval', None) # seconds
        self._inactive_torrent_timeout = kwargs.get('inactive_torrent_timeout', None) # seconds

    def run(self):
        """
        Invoked by multiprocessing.Process.start()
        """
        self._run = True
        try:
            self._run_pre()
            self._ses = self._create_session(self._listen_min, self._listen_max)
            self._watcher = self._create_alert_watcher()
            self._torrent_manager = self._create_torrent_manager()
            self._run_before_loop()
            self._run_loop()
            self._run_post()
        except KeyboardInterrupt:
            if self._verbose:
                self._log.info('%s caught KeyboardInterrupt, exiting.' % self._label)
        except Exception, e:
            if self._out_q:
                item = LibtorrentSessionQueueItem(e.__class__.__name__, str(e))
                self._out_q.put(item)
            if self._verbose:
                self._log.error(str(e))

    def _create_session(self, port_min, port_max):
        flags = 0
        # TODO: Move seedbank version to a version or init file
        s = lt.session(lt.fingerprint("TE", 1, 0, 0, 0), flags)

        settings = get_server_settings()
        s.set_settings(settings)
        if self._peer_id:
            s.set_peer_id(lt.big_number(self._peer_id))
        s.set_alert_mask(ALERT_MASK_DEFAULT)

        listen_flags = lt.listen_on_flags_t.listen_reuse_address | lt.listen_on_flags_t.listen_no_system_port
        listen_interface = None
        s.listen_on(port_min, port_max, listen_interface, listen_flags)
        return s

    def _create_alert_watcher(self):
        if self._verbose:
            self._log.info('Creating ' + self._watcher_class.__name__)
        w = self._watcher_class(label=self._label,
                                session=self._ses,
                                match_list=self._watcher_match_list,
                                loop_limit=self._watcher_loop_limit,
                                tick_interval=self._tick_interval,
                                verbose=self._verbose)
        return w

    def _create_torrent_manager(self):
        if not self._torrent_manager_exec_interval or not self._inactive_torrent_timeout:
            return None
        tm = TorrentManager(label=self._label,
                            verbose=self._verbose,
                            tick_interval=self._tick_interval,
                            exec_interval=self._torrent_manager_exec_interval,
                            inactive_torrent_timeout=self._inactive_torrent_timeout
                            )
        return tm

    def _run_pre(self):
        pass

    def _run_before_loop(self):
        pass

    def _run_loop(self):
        pass

    def _run_post(self):
        self._log.info('%s exiting...' % self._label)
        if self._verbose:
            self._log.info('%s stopping AlertWatcher' % self._label)
        self._watcher.stop()

    def stop(self):
        if self._verbose:
            self._log.info('%s stopping' % self._label)
        self._run = False

    def tick(self):
        self._handle_queue()
        self._check_watcher()
        if self._torrent_manager:
            self._torrent_manager.tick(session=self)
        self._update_session_manager()

    def _check_watcher(self):
        """
        Common logic for checking the watcher and taking appropriate
        action. Executed during tick().
        """
        if self._watcher.is_fully_matched():
            self._out_q.put(LibtorrentSessionQueueItem('watcher_exited', True))

        if not self._watcher.is_alive() and self._stop_on_watcher_exit:
            self._log.info('Internal stop after alert watcher exit')
            self.stop()

    def _handle_queue(self):
        if not self._queue_handler:
            self._log.error('Missing queue handler in LibtorrentSession')

        while self._in_q and not self._in_q.empty():
            item = self._in_q.get()
            self._queue_handler.handle(item)

    def _update_session_manager(self):
        if self._update_counter == 0:
            # send update and reset counter
            torrents = self._ses.get_torrents()
            data = {'torrent_count': len(torrents)}
            self._out_q.put(LibtorrentSessionQueueItem('update', data))
            self._update_counter = self._update_interval
        else:
            self._update_counter -= 1

    def _enable_stats(self, params):
        """
        Used by ServerQueueHandler
        """
        config = params['config']
        if not self._watcher.has_match('torrent_stats_publisher'):
            self._enable_torrent_stats(config)
        if not self._server_stats_publisher:
            self._server_stats_publisher = self._create_server_stats_publisher(config)

    def _enable_torrent_stats(self, config):
        routing_key = config.get(config_helper.MQ_SECTION, 'stats_queue')
        content_type = 'application/json'
        match_tuple = ('torrent_stats_publisher',
                       TorrentStatsPublisher,
                       {'expires_after': 0, 'publisher': RabbitMQPublisher, 'config': config,
                        'routing_key': routing_key, 'content_type': content_type, 'verbose': self._verbose}
                       )
        self._watcher.add_match(match_tuple)
        self._ses.set_alert_mask(ALERT_MASK_STATS)

    def _create_server_stats_publisher(self, config):
        routing_key = config.get(config_helper.MQ_SECTION, 'stats_queue')
        exec_interval = 10
        publisher = ServerStatsPublisher(publisher=RabbitMQPublisher,
                                         config=config,
                                         routing_key=routing_key,
                                         exec_interval=exec_interval,
                                         tick_interval=self._tick_interval,
                                         verbose=self._verbose)
        return publisher

    def _disable_stats(self):
        self._ses.set_alert_mask(ALERT_MASK_DEFAULT)
        self._watcher.remove_match('torrent_stats_publisher')
        self._server_stats_publisher = None

class LibtorrentServerSession(LibtorrentSession):
    def __init__(self, **kwargs):
        kwargs.update({'label': 'server'})
        LibtorrentSession.__init__(self, **kwargs)
        self._watcher_class = ThreadedAlertWatcher
        self._queue_handler = ServerQueueHandler(self)

    def _run_before_loop(self):
        if not self._mongodb_plugin_params:
            self.stop()
            raise LibtorrentSessionException('Invalid mongodb plugin params')

        if self._verbose:
            self._log.info('Adding mongodb session plugin')
            self._log.info('connection_string: ' + self._mongodb_plugin_params['connection_string'])
            self._log.info('torrentdb_ns: ' + self._mongodb_plugin_params['torrentdb_ns'])
            self._log.info('torrent_file_root: ' + self._mongodb_plugin_params['torrent_file_root'])

        self._ses.add_extension('mongodb_torrent_db', self._mongodb_plugin_params)
        self._log.info('Peer id: ' + binascii.a2b_hex(str(self._ses.id())))
        if self._verbose:
            self._log.info('Listening on ' + str(self._listen_min))

        # additional plugins
        self._ses.add_extension('ut_metadata')
        self._ses.add_extension('metadata_transfer')
        self._ses.add_extension('smart_ban')

        # TODO: testing
        #self._ses.add_extension('ut_pex')
        #self._ses.add_extension('lt_trackers')

    def _run_loop(self):
        if not self._run:
            return
        self._watcher.start()
        self._send_server_init_message()

        while self._run:
            self.tick()
            time.sleep(self._tick_interval)

    def _send_server_init_message(self):
        peer_id = str(self._ses.id())
        self._out_q.put(LibtorrentSessionQueueItem('server_init', {'peer_id': peer_id}))

    def tick(self):
        super(LibtorrentServerSession, self).tick()
        if self._server_stats_publisher:
            self._server_stats_publisher.tick(session=self._ses)

    def stop(self):
        super(LibtorrentServerSession, self).stop()
        if self._server_stats_publisher:
            if self._verbose:
                self._log.info('Stopping server stats publisher')
            self._server_stats_publisher.stop()

class LibtorrentClientSession(LibtorrentSession):
    def __init__(self, **kwargs):
        kwargs.update({'label': 'client'})
        LibtorrentSession.__init__(self, **kwargs)
        self._watcher_class = ThreadedAlertWatcher
        self._status_printer = TorrentStatusPrinter(self._label)
        self._queue_handler = ClientQueueHandler(self)

    def _run_before_loop(self):
        self._log.info('Peer id: ' + binascii.a2b_hex(str(self._ses.id())))
        if self._verbose:
            # TODO:
            self._log.info('Listening port range: %s-%s' % (str(self._listen_min), str(self._listen_max)))

    def _run_loop(self):
        if not self._run:
            return
        self._watcher.start()
        while self._run:
            self.tick()
            time.sleep(self._tick_interval)

    def stop(self):
        super(LibtorrentClientSession, self).stop()
