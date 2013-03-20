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
import shutil
import libtorrent as lt

from terasaur.torrent.util import is_valid_info_hash
from seedbank.torrent.util import decode_torrent_data, delete_empty_subdirs

"""
Wrapper object for working with torrent files.
"""
class TorrentFileException(Exception): pass

class TorrentFile(object):
    EXTENSION = '.torrent'

    def __init__(self, **kwargs):
        """
        Keyword arguments:
            torrent_root -- path to seedbank torrent root directory
            info_hash -- hex info hash
            filename -- full path to torrent file
            torrent_data -- bencoded torrent file data as binary string

        Specify either:
            * info_hash -- refers to a torrent already in the seedbank
            * filename -- any torrent file
            * torrent_data -- used to save a torrent file from in-memory data
        """

        self._info_hash = None
        self._torrent_root = None
        self._file_path = None
        self._info = None

        if kwargs.has_key('info_hash') and kwargs.has_key('filename'):
            raise TorrentFileException('Cannot specify both info hash and torrent filename')

        self._torrent_root = kwargs.get('torrent_root', None)
        if self._torrent_root and not os.path.exists(kwargs['torrent_root']):
            raise TorrentFileException('Missing torrent root: %s' % kwargs['torrent_root'])

        if kwargs.has_key('filename'):
            self.__init_from_filename(kwargs)
        elif kwargs.has_key('info_hash'):
            self.__init_from_info_hash(kwargs)

        self._torrent_data = kwargs.get('torrent_data', None)
        if self._torrent_data:
            self.__init_from_torrent_data(**kwargs)

    def __init_from_filename(self, kwargs):
        self.__check_file_path(kwargs['filename'])
        self._file_path = kwargs['filename']

    def __init_from_info_hash(self, kwargs):
        if not is_valid_info_hash(kwargs['info_hash']):
            raise TorrentFileException('Invalid info hash')
        self._info_hash = kwargs['info_hash']
        torrent_path = self.get_path()
        self.__check_file_path(torrent_path)

    def __init_from_torrent_data(self, **kwargs):
        if not self._torrent_root:
            raise TorrentFileException('Missing torrent root directory')

        torrent_info = decode_torrent_data(kwargs.get('torrent_data', None))
        self._info_hash = str(torrent_info.info_hash())
        self._info = torrent_info

    def __check_file_path(self, path):
        if not os.path.exists(path):
            raise TorrentFileException('Missing torrent file: %s' % path)

    def get_path(self):
        if not self._file_path:
            self._file_path = self.__get_path()
        return self._file_path

    def __get_path(self):
        # Load torrent info from file if not already present
        info_hash = self.get_info_hash()
        path = self._torrent_root + \
            TorrentFile.get_subpath(info_hash) + '/' + self.__get_torrent_filename()
        return path

    def __get_torrent_filename(self):
        return self.get_info_hash() + TorrentFile.EXTENSION

    @staticmethod
    def get_subpath(ih_hex):
        subpath_levels = 4
        i = 0
        subpath = ''
        while i < subpath_levels:
            subpath += '/' + ih_hex[i]
            i += 1
        return subpath

    def get_info(self):
        if not self._info:
            self._info = self._get_torrent_info(self._file_path)
        return self._info

    def _get_torrent_info(self, path):
        try:
            info = lt.torrent_info(path)
        except RuntimeError, e:
            # Intercept generic RuntimeError exceptions from libtorrent for known failure
            # conditions.  Allow unknown conditions to bubble up.
            if str(e) == 'expected value (list, dict, int or string) in bencoded string':
                # non-bencoded data in file
                raise TorrentFileException('Invalid torrent file: %s' % str(path))
            elif str(e) == 'Success':
                # empty file
                raise TorrentFileException('Empty torrent file: %s' % str(path))
            elif str(e) == 'Is a directory':
                # a directory, not a file
                raise TorrentFileException('Not a file: %s' % str(path))
            else:
                raise
        return info

    def get_info_hash(self):
        if not self._info_hash:
            info = self.get_info()
            if info:
                self._info_hash = str(info.info_hash())
        return self._info_hash

    def save(self, source=None):
        if source:
            self._save_from_source(source)
        elif self._torrent_data:
            self._save_from_torrent_data()
        else:
            raise TorrentFileException('Cannot save without a source file or bencoded data')

    def _save_from_source(self, source):
        if not os.path.exists(source):
            raise TorrentFileException('Missing torrent file: %s' % str(source))

        # Reset internal file path to ensure file is saved to default location
        self._file_path = None

        info = self._get_torrent_info(source)
        self._info_hash = str(info.info_hash())
        file_path = self.get_path()
        self._make_torrent_subdirs(file_path)
        # TODO: check for failed copy here?
        shutil.copyfile(source, file_path)
        self._file_path = file_path
        self._info = info

    def _save_from_torrent_data(self):
        file_path = self.get_path()
        self._make_torrent_subdirs(file_path)
        fp = open(file_path, 'wb')
        fp.write(self._torrent_data)
        fp.close()

    def _make_torrent_subdirs(self, path):
        subdir = os.path.dirname(path)
        if not os.path.exists(subdir):
            os.makedirs(subdir)

    def delete(self):
        file_path = self.get_path()
        if not self.exists():
            raise TorrentFileException('Missing torrent file: %s' % file_path)
        os.unlink(file_path)
        delete_empty_subdirs(self._torrent_root, os.path.dirname(file_path))

    def exists(self):
        return os.path.exists(self.get_path())

    def move(self, new_dir):
        """
        Move the torrent file to the given directory path.  It's possible
        to override the default subdirectory path logic with this method.

        If the torrent file already exists, move the file.  Otherwise, just
        change the internal file path.
        """
        if new_dir[-1] != '/':
            new_dir += '/'
        old_path = self.get_path()
        new_path = new_dir + self.__get_torrent_filename()
        self._make_torrent_subdirs(new_path)

        if os.path.exists(old_path):
            if os.path.exists(new_path):
                raise TorrentFileException('Destination file already exists: %s' % new_path)
            shutil.move(old_path, new_path)

        # Change internal path last, only if the file operations succeeded
        self._file_path = new_path

    def update(self, data):
        pass

    def get_data(self):
        filename = self.get_path()
        fp = open(filename, 'rb')
        data = fp.read()
        fp.close()
        self._check_torrent_data(data)
        return data

    def _check_torrent_data(self, data):
        decode = lt.bdecode(data)
        if not decode.has_key('info'):
            raise TorrentFileException('Invalid torrent file (missing info key)')
        if not decode['info'].has_key('pieces'):
            raise TorrentFileException('Invalid torrent file (missing pieces key)')
