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

from terasaur.db import torrent_db
from seedbank.torrent.torrent_file import TorrentFile
from terasaur.torrent.util import is_valid_info_hash
from terasaur.mixin.timestamp import TimestampMixin

class TorrentException(Exception): pass

"""
Persistent torrent object, data stored in mongodb

Note that datetime values are always UTC in mongodb
"""
class Torrent(TimestampMixin):
    __slots__ = ('info_hash', 'name', 'size', 'data_root', 'added', 'last_accessed',
                 '_torrent_file', '_torrent_root')

    """
    string info_hash (unique)
    string name
    long size
    datetime added
    datetime last_accessed
    string file_root_directory
    datetime data_integrity_failure
    list files -> [{path: '', size: ''}, ...]
    """

    def __init__(self, **kwargs):
        """
        Keyword arguments:
            filename -- full path to torrent file
            torrent_root -- path to seedbank torrent root directory
        """
        self.info_hash = None
        self.name = None
        self.size = None
        self.data_root = None
        self.added = None
        self.last_accessed = None
        self._torrent_file = None
        self._torrent_root = kwargs.get('torrent_root', None)

        # Parse and import info from torrent file if given
        if kwargs.has_key('filename'):
            if self._torrent_root:
                self._torrent_file = TorrentFile(filename=kwargs['filename'], torrent_root=self._torrent_root)
            else:
                self._torrent_file = TorrentFile(filename=kwargs['filename'])
            self.info_hash = str(self._torrent_file.get_info_hash())
            self.name = self._torrent_file.get_info().name()

    @staticmethod
    def find(**kwargs):
        """
        Find single:
            - Query by info hash and return Torrent object
        Find multiple:
            - Return list of Torrent objects
        """
        info_hash = kwargs.get('info_hash', None)
        if info_hash is not None:
            return Torrent._find_single(**kwargs)
        else:
            return Torrent._find_multiple(**kwargs)

    @staticmethod
    def _find_single(**kwargs):
        info_hash = kwargs.get('info_hash', None)
        torrent_root = kwargs.get('torrent_root', None)
        Torrent._validate_info_hash(info_hash)
        data = torrent_db.get(info_hash)
        t = Torrent._data_to_torrent(data, torrent_root)
        return t

    @staticmethod
    def _find_multiple(**kwargs):
        query = kwargs.get('query', None)
        torrent_root = kwargs.get('torrent_root', None)
        data_list = torrent_db.find(query)
        torrent_list = []
        for data in data_list:
            t = Torrent._data_to_torrent(data, torrent_root)
            torrent_list.append(t)
        return torrent_list

    @staticmethod
    def _data_to_torrent(data, torrent_root=None):
        if data:
            t = Torrent(torrent_root=torrent_root)
            t.info_hash = data['info_hash']
            t.name = data['name']
            t.data_root = data['data_root']
            t.added = data['added']
            t.last_accessed = data['last_accessed']
            if torrent_root:
                t._torrent_file = TorrentFile(info_hash=t.info_hash, torrent_root=torrent_root)
        else:
            t = None
        return t

    def save(self):
        self.validate()
        self._save_torrent_file()
        save_dict = self._get_save_dict()
        torrent_db.save(save_dict)
        self.added = save_dict['added']

    def _save_torrent_file(self):
        """
        Save torrent file to seedbank torrent tree if:
            * We have a TorrentFile instance
            * The TorrentFile path isn't already in the torrent tree
        """
        if not self._torrent_file:
            return

        if self._torrent_file.get_path()[:len(self._torrent_root)] == self._torrent_root:
            return

        # copy torrent file into seedbank torrents tree
        self._torrent_file.save(self._torrent_file.get_path())

        # replace torrent file instance.  throws exception on error.
        new_tf = TorrentFile(torrent_root=self._torrent_root, info_hash=self.info_hash)
        self._torrent_file = new_tf

    def validate(self):
        self._validate_info_hash(self.info_hash)
        if not self.data_root:
            raise TorrentException('Missing torrent data root')

    @staticmethod
    def _validate_info_hash(info_hash):
        if not info_hash:
            raise TorrentException('Missing info hash')

        if not is_valid_info_hash(info_hash):
            raise TorrentException('Invalid info hash')

    def _get_save_dict(self):
        added_date = self.added if self.added else self._get_now()
        save_dict = {
            'info_hash': self.info_hash,
            'name': self.name,
            'data_root': self.data_root,
            'added': added_date,
            'last_accessed': self.last_accessed
            }
        return save_dict

    def get_info(self):
        info = None
        if self._torrent_file:
            info = self._torrent_file.get_info()
        return info

    def delete(self):
        self._validate_info_hash(self.info_hash)
        self._delete_torrent_file()
        torrent_db.delete(self.info_hash)

    def _delete_torrent_file(self):
        # TODO: Note a missing torrent file to allow returning a
        #    warning.  Don't throw an exception if missing, though.
        if not self._torrent_file:
            raise TorrentException('Insufficient information trying to delete torrent')

        if self._torrent_file.exists():
            self._torrent_file.delete()

