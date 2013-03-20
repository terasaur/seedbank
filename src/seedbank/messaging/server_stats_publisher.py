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
import binascii

from terasaur.messaging.rabbitmq_publisher import SelfManagingRabbitMQPublisher
from seedbank.mixin.tick_counter import TickCounterMixin
from terasaur.mixin.timestamp import TimestampMixin

class ServerStatsPublisher(SelfManagingRabbitMQPublisher, TickCounterMixin, TimestampMixin):
    def __init__(self, **kwargs):
        """
        Query information from libtorrent session object and publish
        a server stats message to the stats message queue.  The tick
        function should be called from the LibtorrentSession event loop.
        """
        SelfManagingRabbitMQPublisher.__init__(self, **kwargs)
        # self._log comes from RabbitMQPublisher
        TickCounterMixin.__init__(self, **kwargs)

    def _tick(self, **kwargs):
        """
        Called from TickCounterMixin::tick

        :Parameters:
            - `session`: :class: libtorrent.session
        """
        session = kwargs.get('session', None)
        message = self._get_stats_message(session)
        self.publish(message)

    def _get_stats_message(self, session):
        status = session.status()
        torrents = session.get_torrents()
        data = {
            'timestamp': self._get_now_timestamp(),
            'peer_id': binascii.a2b_hex(str(session.id())),
            'num_torrents' : len(torrents),
            'num_peers' : status.num_peers,
            'num_unchoked' : status.num_unchoked,
            'allowed_upload_slots' : status.allowed_upload_slots,
            'upload_rate' : status.upload_rate,
            'total_upload' : status.total_upload,
            'download_rate' : status.download_rate,
            'total_download' : status.total_download,
            'payload_upload_rate' : status.payload_upload_rate,
            'total_payload_upload' : status.total_payload_upload,
            'payload_download_rate' : status.payload_download_rate,
            'total_payload_download' : status.total_payload_download,
            'ip_overhead_upload_rate' : status.ip_overhead_upload_rate,
            'total_ip_overhead_upload' : status.total_ip_overhead_upload,
            'ip_overhead_download_rate' : status.ip_overhead_download_rate,
            'total_ip_overhead_download' : status.total_ip_overhead_download,
            'dht_upload_rate' : status.dht_upload_rate,
            'total_dht_upload' : status.total_dht_upload,
            'dht_download_rate' : status.dht_download_rate,
            'total_dht_download' : status.total_dht_download,
            'tracker_upload_rate' : status.tracker_upload_rate,
            'tracker_download_rate' : status.tracker_download_rate,
            'total_tracker_download' : status.total_tracker_download,
            'total_tracker_upload' : status.total_tracker_upload
            }
        return json.dumps(data)
