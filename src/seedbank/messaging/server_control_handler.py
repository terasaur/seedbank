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

# TODO: rename file to control_message_handler.py

from terasaur.messaging.rabbitmq_message_handler import ControlMessageHandler
from seedbank.server.libtorrent_session import LibtorrentSessionQueueItem
from seedbank.messaging.server_control_message import ServerPingResponseMessage
import seedbank.server.shared as seedbank_shared

class SeedbankControlMessageHandler(ControlMessageHandler):
    def _handle_action(self, action, data):
        if action == 'publish_stats':
            self._handle_publish_stats(bool(data['enable']))
        elif action == 'upload':
            self._handle_upload(data)
        elif action == 'ping_request':
            self._handle_ping(data)
        else:
            self._log.warning('Control message received without valid action (%s)' % action)

    def _handle_publish_stats(self, enable):
        if enable:
            config = self._server._get_config()
            item = LibtorrentSessionQueueItem('publish_stats', {'enable': True, 'config': config})
        else:
            item = LibtorrentSessionQueueItem('publish_stats', {'enable': False})
        self._log.info('Received publish_stats control message (%s)' % enable)
        seedbank_shared.session_manager.send('server', item)

    def _handle_upload(self, data):
        if not data.has_key('upload_action'):
            self._log.error('Missing upload_action param in upload control message')
            return
        if not data.has_key('info_hash'):
            self._log.error('Missing info_hash param in upload control message')
            return

        upload_action = data['upload_action']
        upload_manager = seedbank_shared.upload_manager
        if upload_action == 'start':
            if data.has_key('torrent_file'):
                torrent_file = data['torrent_file']
            else:
                torrent_file = None
            upload_manager.start(info_hash=data['info_hash'], torrent_file=torrent_file)
        elif upload_action == 'stop':
            upload_manager.stop(info_hash=data['info_hash'])
        elif upload_action == 'cancel':
            upload_manager.cancel(info_hash=data['info_hash'])
        elif upload_action == 'delete':
            upload_manager.delete(info_hash=data['info_hash'])
        elif upload_action == 'status':
            upload_manager.status(info_hash=data['info_hash'])
        else:
            self._log.error('Invalid upload_action param in upload control message')

    def _handle_torrent(self):
        pass

    def _handle_ping(self, data):
        if self._verbose:
            self._log.info('Sending ping reply (reply_to: %s, correlation_id: %s)' % (data['reply_to'], data['correlation_id']))
        message = ServerPingResponseMessage(correlation_id=data['correlation_id'])
        seedbank_shared.mq_out.publish(str(message), routing_key=data['reply_to'])

        return
        count = 0
        while count < 100:
            print 'sending ping reply (%i)' % count
            seedbank_shared.mq_out.publish(str(message), routing_key=data['reply_to'])
            count += 1
