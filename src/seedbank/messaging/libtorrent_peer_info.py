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
Extract information from a libtorrent peer_info struct and translate
data into a more human-consumable form.
"""

class LibtorrentPeerInfo(object):
    _CONNECTION_TYPES = ['standard_bittorrent', 'web_seed', 'http_seed', 'bittorrent_utp']

    _FLAGS = [('interesting', 0x1),
              ('choked', 0x2),
              ('remote_interested', 0x4),
              ('remote_choked', 0x8),
              ('supports_extensions', 0x10),
              ('local_connection', 0x20),
              ('handshake', 0x40),
              ('connecting', 0x80),
              ('queued', 0x100),
              ('on_parole', 0x200),
              ('seed', 0x400),
              ('optimistic_unchoke', 0x800),
              ('snubbed', 0x1000),
              ('upload_only', 0x2000),
              ('endgame_mode', 0x4000),
              ('rc4_encrypted', 0x100000),
              ('plaintext_encrypted', 0x200000)
              ]

    _PEER_SOURCE_FLAGS = [('tracker', 0x1),
                          ('dht', 0x2),
                          ('pex', 0x4),
                          ('lsd', 0x8),
                          ('resume_data', 0x10),
                          ('incoming', 0x20)]

    def __init__(self, pi=None):
        self.data = self._extract_data(pi)

    def _extract_data(self, pi):
        if not pi:
            return None

        (addr, port) = pi.ip # tuple
        data = {
            'flags': self._extract_flags(pi),
            'source': self._extract_source(pi),
            'ip_addr': addr, # string
            'ip_port': port, # int
            'up_speed': pi.up_speed, # int
            'down_speed': pi.down_speed, # int
            'payload_up_speed': pi.payload_up_speed, # int
            'payload_down_speed': pi.payload_down_speed, # int
            # requires geoip
            #'country': pi.country, # char[2]
            #'inet_as_name': pi.inet_as_name, # string
            #'inet_as': pi.inet_as, # int
            'load_balancing': pi.load_balancing, # size_type
            'failcount': pi.failcount, # int
            'downloading_progress': pi.downloading_progress, # int
            'client': pi.client, # string
            'connection_type': LibtorrentPeerInfo._CONNECTION_TYPES[pi.connection_type],
            'remote_dl_rate': pi.remote_dl_rate, # int
            'rtt': pi.rtt, # int

            # TODO: enable after next libtorrent svn update
            # 'num_pieces': pi.num_pieces, # int
            'progress': pi.progress # float
            }
        return data

    def _extract_flags(self, pi):
        # pi.flags: unsigned int
        return self._bitmask_to_labels(pi.flags, LibtorrentPeerInfo._FLAGS)

    def _extract_source(self, pi):
        return self._bitmask_to_labels(pi.source, LibtorrentPeerInfo._PEER_SOURCE_FLAGS)

    def _bitmask_to_labels(self, bitmask, label_tuples):
        labels = []
        for (label, value) in label_tuples:
            if bitmask & value:
                labels.append(label)
        return labels
