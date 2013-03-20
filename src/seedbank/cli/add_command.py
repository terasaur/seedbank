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

import os

from seedbank.cli.command import Command
from seedbank.torrent.torrent import Torrent
import terasaur.config.config_helper as config_helper

class AddCommand(Command):
    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)
        self._torrent_file = kwargs.get('torrent_file', None)
        self._data_root = kwargs.get('data_root', None)

        if kwargs.has_key('torrent_root'):
            self._torrent_root = kwargs.get('torrent_root')
        else:
            self._torrent_root = self._config.get(config_helper.MAIN_SECTION, 'torrent_file_root')

    def execute(self):
        if not self._check_required_params():
            return

        self._print('torrent_file: %s\n' % self._torrent_file)
        self._print('data_root: %s\n' % self._data_root)
        #self._print('torrent_root: ' + self._torrent_root)

        # Convert data_root relative path to absolute path
        if self._data_root[0] != '/':
            self._data_root = os.path.abspath(self._data_root)

        t = Torrent(filename=self._torrent_file, torrent_root=self._torrent_root)
        t.data_root = self._data_root

        if not self._check_duplicate_torrent(t):
            return
        if not self._check_torrent_root_contents(t):
            return

        # TODO: check for torrent file already exists in torrent root

        t.save()

        # TODO: delete torrent file if save fails

        self._print('Torrent added\n')

    def _check_required_params(self):
        if not self._torrent_file:
            self._print('Missing torrent file\n')
            return False
        if not self._torrent_root:
            self._print('Missing torrent file root directory\n')
            return False
        if not self._data_root:
            self._print('Missing torrent data directory\n')
            return False
        if not os.path.exists(self._data_root):
            self._print('Missing or invalid torrent data directory: %s\n' % (self._data_root))
            return False
        if not os.access(self._torrent_root, os.W_OK):
            self._print('You do not have write permission on the seed bank torrents directory\n')
            return False
        return True

    def _check_duplicate_torrent(self, torrent):
        """
        Report error if the torrent already exists in the torrent db
        """
        found = Torrent.find(info_hash=torrent.info_hash)
        if found and (found.info_hash == torrent.info_hash):
            self._print('Torrent ' + torrent.name + ' already exists\n')
            return False
        return True

    def _check_torrent_root_contents(self, torrent):
        """
        Basic sanity check on the torrent data file tree.  Make sure all of the
        files exist at the correct paths.  This does not verify file data or
        checksums.
        """
        # Enforce absolute paths when checking torrent data
        if not self._data_root or self._data_root[0] != '/':
            self._print('Torrent data root was not an absolute path\n')
            return False

        info = torrent.get_info()
        files = info.files()
        for entry in files:
            if not os.path.exists(self._data_root + '/' + entry.path):
                self._print('Missing file in torrent data root: ' + entry.path + '\n')
                return False
        return True
