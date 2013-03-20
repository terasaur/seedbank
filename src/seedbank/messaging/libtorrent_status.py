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

import sys

"""
Class for displaying libtorrent session status to stdout.  Used for testing
and debugging.
"""
class StatusPrinter(object):
    def __init__(self, label):
        self._label = label
        self._torrent_status_printer = TorrentStatusPrinter(label)

    def basic(self, session):
        self._print_session_status(session, False)

    def extended(self, session):
        self._print_session_status(session, True)

    def _print_session_status(self, session, extended):
        status = session.status()
        torrents = session.get_torrents()
        if extended:
            self._print_extended_status(status, torrents)
        else:
            self._print_basic_status(status, torrents)

    def _print_basic_status(self, status, torrents):
        print '%s: %.2f uploaded, %d peers, %d torrents' % \
            (self._label,
             status.total_upload,
             status.num_peers,
             len(torrents)
             )

    def _print_extended_status(self, status, torrents):
        #has_incoming_connections
        print '%s: peers: %d unchoked: %d upload slots: %d torrents: %d' % \
            (self._label,
             status.num_peers,
             status.num_unchoked,
             status.allowed_upload_slots,
             len(torrents)
             )

        print '    overall: %.2f %.2f %.2f %.2f' % \
            (status.upload_rate,
             status.total_upload,
             status.download_rate,
             status.total_download)

        print '    payload: %.2f %.2f %.2f %.2f' % \
            (status.payload_upload_rate,
            status.total_payload_upload,
            status.payload_download_rate,
            status.total_payload_download)

        print '    ip overhead: %.2f %.2f %.2f %.2f' % \
            (status.ip_overhead_upload_rate,
            status.total_ip_overhead_upload,
            status.ip_overhead_download_rate,
            status.total_ip_overhead_download)

        print '    dht: %.2f %.2f %.2f %.2f' % \
            (status.dht_upload_rate,
            status.total_dht_upload,
            status.dht_download_rate,
            status.total_dht_download)

        print '    tracker: %.2f %.2f %.2f %.2f' % \
            (status.tracker_upload_rate,
            status.tracker_download_rate,
            status.total_tracker_download,
            status.total_tracker_upload)

        #status.total_redundant_bytes
        #status.total_failed_bytes

        """
        optimistic_unchoke_counter
        unchoke_counter

        dht_nodes
        dht_node_cache
        dht_torrents
        dht_global_nodes
        """

        self._print_torrents(torrents)

    def print_torrents(self, session):
        torrents = session.get_torrents()
        sys.stdout.flush()

    def _print_torrents(self, torrents):
        for torrent in torrents:
            self._torrent_status_printer.print_single(torrent)

class TorrentStatusPrinter(object):
    def __init__(self, label):
        self._label = label
        self._state_str = ['queued', 'checking', 'downloading metadata', \
            'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']

    def print_single(self, torrent):
        label = self._label
        s = torrent.status()
        print '%s %s (%s): %.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d conns: %d) state: %s, err: %s desc: %s\n' % \
            (label, torrent.name(), torrent.info_hash(), s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
            s.num_peers, s.num_connections, self._state_str[s.state], s.error, ','.join(self._get_torrent_descriptors(s)))
        print '%s times: %i active, %i finished, %i seeding, %i since download, %i since upload' % \
            (self._label, s.active_time, s.finished_time, s.seeding_time, s.time_since_download, s.time_since_upload)
        self._print_peers(torrent)

    def _get_torrent_descriptors(self, status):
        l = []
        if status.paused:
            l.append('paused')
        if status.auto_managed:
            l.append('auto_managed')
        if status.sequential_download:
            l.append('sequential_download')
        if status.is_seeding:
            l.append('seeding')
        if status.is_finished:
            l.append('finished')
        if status.has_metadata:
            l.append('has_metadata')
        return l

    def _print_peers(self, torrent):
        peers = torrent.get_peer_info()
        for peer in peers:
            self._print_peer_info(peer)

    def _print_peer_info(self, peer):
        print '%s peer: %s' % (self._label, str(peer.ip))

