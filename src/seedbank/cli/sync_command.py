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

from seedbank.cli.command import Command, CommandException
from seedbank.torrent.torrent import Torrent

class SyncCommand(Command):
    """
    Synchronize torrents in local seed bank with terasaur web application.
    """
    def execute(self):
        self._conn = None # placeholder
        self._conn.login()
        self._println('Getting torrent list')
        remote_torrents = self._conn.get_conn().getTorrentList()
        if not self._check_login_error(remote_torrents):
            self._println('Got seed bank not found error, exiting')
            return
        local_torrents = self._get_local_torrents()
        self._handle_sync(local_torrents, remote_torrents)
        self._conn.logout()

    def _check_login_error(self, remote_torrents):
        okay = True
        pseed_err_str = 'Seed bank not found for peer_id'
        if len(remote_torrents) == 1 and remote_torrents[0][:len(pseed_err_str)] == pseed_err_str:
            self._println(remote_torrents[0])
            self._conn.logout()
            okay = False
        return okay

    def _get_local_torrents(self):
        torrents = Torrent.find()
        local_torrents = []
        for t in torrents:
            local_torrents.append(t.info_hash)
        return local_torrents

    def _handle_sync(self, local_torrents, remote_torrents):
        # Compare the remote list with the local list from the config
        # file.
        # to_link: items in local list not in remote list
        # to_unlink: items in remote list not in local list
        to_link = local_torrents
        to_unlink = []

        for ih in remote_torrents:
            torrent = Torrent.find(info_hash=ih)
            if torrent is None:
                self._println('Need to unlink ' + str(ih))
                to_unlink.append(ih)
            else:
                to_link.remove(ih)

        self._unlink_torrents(to_unlink)
        self._add_torrents(to_link)

    def _unlink_torrents(self, to_unlink):
        # Remove missing torrents.
        if len(to_unlink) > 0:
            self._println('Removing defunct torrents')
            self._conn.get_conn().unlinkTorrents(to_unlink)
        else:
            self._println('No torrents to remove')

    def _add_torrents(self, to_link):
        # Add new torrents.
        if len(to_link) > 0:
            self._println('Adding new torrents')
            self._conn.get_conn().linkTorrents(to_link)
        else:
            self._println('No torrents to add')
