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

import libtorrent as lt
import terasaur.log.log_helper as log_helper
from seedbank.messaging.libtorrent_status import TorrentStatusPrinter
from seedbank.mixin.tick_counter import TickCounterMixin
from seedbank.server.session_queue_item import LibtorrentSessionQueueItem

class TorrentManager(TickCounterMixin):
    """
    Encapsulates logic for adding/removing torrents to the libtorrent session.  This
    includes tracking uploads and expiring inactive torrents.
    """
    def __init__(self, **kwargs):
        TickCounterMixin.__init__(self, **kwargs)
        self._verbose = kwargs.get('verbose', False)
        self._label = kwargs.get('key', '')
        self._log = log_helper.get_logger(self.__class__.__name__)
        self._torrents = {} # tracked torrents

        if self._verbose:
            self._printer = TorrentStatusPrinter('server')
        else:
            self._printer = None

        # torrent timeout values
        self._inactive_torrent_timeout = kwargs.get('inactive_torrent_timeout', 60)

    def _tick(self, **kwargs):
        """
        Called from TickCounterMixin::tick

        :Parameters:
            - `session`: :class: LibtorrentSession
        """
        try:
            session = kwargs.get('session', None) # LibtorrentSession object
            self._check_libtorrent_torrents(session._ses)
            self._check_torrents(session)
        except Exception, e:
            self._log.error(str(e))

    def _check_libtorrent_torrents(self, lt_session):
        torrents = lt_session.get_torrents()
        for torrent in torrents:
            if self._printer:
                self._printer.print_single(torrent)
            self._check_expiration(lt_session, torrent)

    def _check_expiration(self, lt_session, torrent):
        if self._is_expired(torrent):
            self._log.info('Removing inactive torrent: %s (%s)' % (torrent.name(), torrent.info_hash()))
            self._remove_torrent(lt_session, torrent)

    def _is_expired(self, torrent):
        s = torrent.status()
        if s.time_since_download > self._inactive_torrent_timeout and s.time_since_upload > self._inactive_torrent_timeout:
            return True
        else:
            return False

    def _check_torrents(self, session):
        keys = self._torrents.keys()
        for info_hash in keys:
            torrent = self._torrents[info_hash]
            try:
                #self._status_printer.print_single(t)
                # pause torrent if progress is 100%
                status = torrent.status()
                if status.progress == 1 and not status.paused:
                    self._finish_completed_torrent(session, torrent)
            except Exception, e:
                self._log.info('Error checking upload: %s' % str(e))

    def _finish_completed_torrent(self, session, torrent):
        torrent.pause()
        self._send_torrent_done_message(session, torrent)
        self._remove_torrent(session._ses, torrent)

    def _send_torrent_done_message(self, session, torrent):
        torrent_info = torrent.get_torrent_info()
        info_hash = str(torrent_info.info_hash())
        message = {
            'info_hash': info_hash,
            'torrent_root': torrent.save_path()
            }
        item = LibtorrentSessionQueueItem('torrent_finished', message)
        session._out_q.put(item)

    def add_torrent(self, session, params):
        info_hash = params['info_hash']
        # convert params into torrent_info
        e = lt.bdecode(params['torrent_file'])
        torrent_info = lt.torrent_info(e)

        # sanity check: info_hash values must match
        if str(torrent_info.info_hash()) != info_hash:
            raise Exception('Error adding torrent (%s != %s)' % (torrent_info.info_hash(), info_hash))

        # add torrent to session
        add_torrent_params = {
            'ti': torrent_info,
            'save_path': str(params['torrent_root']) # cast to regular string; the libtorrent c++ bindings don't like unicode
            }

        torrent = session._ses.add_torrent(add_torrent_params)
        if torrent:
            if self._torrents.has_key(info_hash):
                session._log.error('Cannot add duplicate torrent to session (%s)' % (info_hash))
            else:
                self._torrents[info_hash] = torrent
                session._log.info('Added torrent to session for upload: %s (%s)' % (torrent.name(), info_hash))
        else:
            session._log.error('Error adding torrent to libtorrent session')
            # TODO: how to determine errors here?

    def remove_torrent(self, session, info_hash):
        pass

    def _remove_torrent(self, lt_session, torrent):
        lt_session.remove_torrent(torrent)
        info_hash = str(torrent.info_hash())
        if self._torrents.has_key(info_hash):
            del self._torrents[info_hash]

    def add_peer(self, session, params):
        if len(self._torrents) < 1:
            raise Exception('Cannot add peer to a session with no active torrents')
        if not params:
            raise Exception('Missing params in add_peer handler')
        if not params.has_key('peer') or not params['peer']:
            raise Exception('Missing peer address/port information')
        if not params.has_key('info_hash') or not params['info_hash']:
            raise Exception('Missing info_hash')

        ip_port_tuple = params['peer']
        info_hash = params['info_hash']
        if session._verbose:
            session._log.info('%s adding new peer %s to %s' % (session._label, str(ip_port_tuple), info_hash))
        self._torrents[info_hash].connect_peer(ip_port_tuple, 0)
