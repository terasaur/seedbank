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

import json

from terasaur.messaging.rabbitmq_publisher import SelfManagingRabbitMQPublisher
from seedbank.server.alert_match import TorrentStatsAlertMatch
from terasaur.mixin.timestamp import TimestampMixin
from seedbank.messaging.libtorrent_peer_info import LibtorrentPeerInfo

class TorrentStatsPublisher(SelfManagingRabbitMQPublisher, TorrentStatsAlertMatch, TimestampMixin):
    def __init__(self, **kwargs):
        SelfManagingRabbitMQPublisher.__init__(self, **kwargs)
        TorrentStatsAlertMatch.__init__(self, **kwargs)

    def _on_match(self, alert):
        message = self._get_stats_message(alert)
        self.publish(message)

    def _get_stats_message(self, alert):
        #transferred = []
        #for elem in alert.transferred():
        #    transferred.append(copy.deepcopy(elem))
        peers = self._get_peer_info(alert)
        data = {
            'info_hash': str(alert.handle.info_hash()),
            'name': alert.handle.name(),
            'interval': alert.interval,
            'transferred': alert.transferred,
            'timestamp': self._get_now_timestamp(),
            'peers': peers
            }
        return json.dumps(data)

    def _get_peer_info(self, alert):
        peer_info_list = alert.handle.get_peer_info()
        peers = []
        for peer_info in peer_info_list:
            pi = LibtorrentPeerInfo(peer_info)
            peers.append(pi.data)
        return peers
