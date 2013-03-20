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
#@PydevCodeAnalysisIgnore
import os
import libtorrent as lt
from seedbank.cli.command import Command

class CreateCommand(Command):
    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)
        self._output_file = kwargs.get('output_file', None)
        self._torrent_data = kwargs.get('torrent_data', None)
        self._tracker = kwargs.get('tracker', None)
        self._overwrite = bool(kwargs.get('overwrite', False))
        self._show_progress = bool(kwargs.get('show_progress', False))
        self._comment = kwargs.get('comment', None)
        self._private = kwargs.get('private', False)

        # TODO: look for tracker url(s) in self._config, CREATE_TORRENT_SECTION

    def execute(self):
        if not self._torrent_data:
            raise ValueError('Missing file or directory path for torrent data')
        if not self._output_file:
            raise ValueError('Missing torrent output file')

        if os.path.exists(self._output_file) and not self._overwrite:
            self._println('Torrent file already exists')
            return

        input = os.path.abspath(self._torrent_data)

        fs = lt.file_storage()
        lt.add_files(fs, input)
        if fs.num_files() == 0:
            self._println('Error: no files added to torrent')
            return

        piece_length = self._calculate_piece_length()
        #pad_size_limit = 4 * 1024 * 1024
        pad_size_limit = -1

        t = lt.create_torrent(fs, piece_length, pad_size_limit)

        # TODO: support multiple tracker urls
        if not self._tracker:
            raise ValueError('Missing tracker URL')
        t.add_tracker(self._tracker)

        creator = 'terasaur seedbank %s' % lt.version
        t.set_creator(creator)
        if self._comment:
            t.set_comment(self._comment)
        t.set_priv(self._private)

        data_dir = os.path.split(input)[0]
        if self._show_progress:
            lt.set_piece_hashes(t, data_dir, lambda x: self._print('.'))
            self._println('')
        else:
            lt.set_piece_hashes(t, data_dir)

        self._write_output_file(t, self._output_file)

    def _calculate_piece_length(self):
        # TODO: is the libtorrent algorithm a good long term solution?
        # 32 K pieces
        #return 32 * 1024
        return 0

    def _write_output_file(self, torrent, filepath):
        self._println('Writing torrent file: %s' % (filepath))
        data = lt.bencode(torrent.generate())
        fp = open(filepath, 'wb')
        fp.write(data)
        fp.close()
