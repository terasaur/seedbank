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

"""
Logic for handling inbound queue items for LibtorrentSession instances.  This
class makes state changes and performs other internal manipulation of the
LibtorrentSession class.
"""

import libtorrent as lt
import time

class LibtorrentSessionQueueHandler(object):
    def __init__(self, session):
        self.session = session # LibtorrentSession instance

    def handle(self, item):
        """ Handle wrapper.  Exceptions will cause serious problems if
        not caught here. """
        try:
            self._handle(item)
        except Exception, e:
            self.session._log.error('Error handling queue item: %s' % str(e))

    def _handle(self, item):
        # Handle common commands
        if item.type == 'alert_list':
            self._handle_queue_alert_list(item.value)
        if item.type == 'stop':
            self.session.stop()
        if item.type == 'set_verbose':
            self.session._verbose = item.value
        if item.type == 'sleep':
            if self.session._verbose:
                self.session._log.info('Sleeping... (%f)', item.value)
            time.sleep(item.value)

        # Delegate to client and server for non-shared commands
        self._delegate(item)

    def _handle_queue_alert_list(self, alert_list):
        if self._watcher is not None:
            for item in alert_list:
                self._watcher.add_match(item)
        else:
            self._watcher_match_list = alert_list

class ServerQueueHandler(LibtorrentSessionQueueHandler):
    def _delegate(self, item):
        if item.type == 'publish_stats':
            self._handle_publish_stats(item.value)

    def _handle_publish_stats(self, params):
        if not self.session._watcher:
            self.session._log.warning('Cannot handle publish_stats message, null watcher')
            return

        if params['enable']:
            self.session._enable_stats(params)
        else:
            self.session._disable_stats()

class ClientQueueHandler(LibtorrentSessionQueueHandler):
    def _delegate(self, item):
        if item.type == 'add_torrent':
            self._handle_add_torrent(item.value)
        if item.type == 'add_peer':
            self._handle_add_peer(item.value)
        if item.type == 'bump_torrent':
            self._handle_bump_torrent(item.value)
        if item.type == 'stop_torrent':
            self._handle_stop_torrent(item.value)

    def _handle_add_torrent(self, params):
        self.session._torrent_manager.add_torrent(self.session, params)

    def _handle_add_peer(self, params):
        self.session._torrent_manager.add_torrent(self.session, params)

    def _handle_bump_torrent(self, params):
        info_hash_hex = str(params['info_hash'])
        info_hash = lt.big_number(info_hash_hex)
        torrent_handle = self.session._ses.find_torrent(info_hash)
        if not torrent_handle:
            self.session._log.error('Missing torrent handle trying to bump %s' % info_hash)
            return

        self.session._log.info('Pausing torrent %s' % info_hash)
        torrent_handle.pause()
        time.sleep(0.5)
        self.session._log.info('Resuming torrent %s' % info_hash)
        torrent_handle.resume()

    def _handle_stop_torrent(self, params):
        info_hash_hex = str(params['info_hash'])
        info_hash = lt.big_number(info_hash_hex)

        th = self.session._ses.find_torrent(info_hash)
        if not th:
            self.session._log.error('Missing torrent handle trying to stop %s' % info_hash)
            return

        print 'torrent handle: ' + str(th.info_hash())

        torrents = self.session._ses.get_torrents()
        print ''
        print ''
        for t in torrents:
            print 'info_hash: ' + str(t.info_hash())

        print ''
        print ''
        th = self.session._ses.find_torrent(info_hash)
        if not th:
            self.session._log.error('Missing torrent handle trying to stop %s' % info_hash)
            return

        return

        self.session._log.info('Removing torrent from session %s' % info_hash)

        self.session._ses.remove_torrent(th)


