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

class RemoveCommand(Command):
    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)
        self._info_hash = kwargs.get('info_hash', None)

        if kwargs.has_key('torrent_root'):
            self._torrent_root = kwargs.get('torrent_root')
        else:
            self._torrent_root = self._config.get(config_helper.MAIN_SECTION, 'torrent_file_root')

    def execute(self):
        if not self._check_required_params():
            return

        t = Torrent.find(info_hash=self._info_hash, torrent_root=self._torrent_root)
        if t:
            self._delete(t)
        else:
            self._print('Torrent not found for info hash %s\n' % self._info_hash)

    def _delete(self, torrent):
        try:
            torrent.delete()
            self._print('Removed torrent %s (%s)\n' % (torrent.name, torrent.info_hash))
        except OSError, e:
            # Common problem is an 'Operation not permitted' error deleting a file
            self._print('Unable to remove torrent (%s)\n' % str(e))

    def _check_required_params(self):
        if not self._info_hash:
            self._print('Missing info hash\n')
            return False
        if not self._torrent_root:
            self._print('Missing torrent file root directory\n')
            return False
        if not os.access(self._torrent_root, os.W_OK):
            self._print('You do not have write permission on the seed bank torrents directory\n')
            return False
        return True
