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
import shutil

from terasaur.db import mongodb_db
from seedbank.db import upload_db
from terasaur.torrent.util import is_valid_info_hash
from seedbank.torrent.util import decode_torrent_data
from seedbank.torrent.torrent_file import TorrentFile, TorrentFileException
from terasaur.mixin.timestamp import TimestampMixin
from terasaur.config.config_helper import MAIN_SECTION
from seedbank.torrent.util import delete_empty_subdirs

class UploadException(Exception): pass

"""
Persistent torrent object, data stored in mongodb

Note that datetime values are always UTC in mongodb
"""
class Upload(TimestampMixin):
    __slots__ = ('info_hash', 'size', 'torrent_root', 'finished',
                 'date_created', 'last_updated', 'torrent_file', 'torrent_data', 'torrent_info')

    def __init__(self, **kwargs):
        self.info_hash = kwargs.get('info_hash', None)
        self.size = 0
        self.torrent_root = None
        self.finished = False
        self.date_created = None
        self.last_updated = None
        self.torrent_file = None # TorrentFile
        self.torrent_data = None # cached bencoded torrent file data
        self.torrent_info = None # cached libtorrent.torrent_info

        if kwargs.has_key('torrent_data'):
            self._init_from_torrent_data(**kwargs)

    def _init_from_torrent_data(self, **kwargs):
        """
        Set properties from bencoded torrent data.  Requires a ConfigParser
        parameter to determine the torrent_root path.
        """
        config = kwargs.get('config', None)
        if not config:
            raise UploadException('Missing config param')
        torrent_data = kwargs.get('torrent_data', None)
        if not torrent_data:
            raise UploadException('Missing torrent_data param')

        # decode torrent file
        torrent_info = decode_torrent_data(torrent_data)
        info_hash = str(torrent_info.info_hash())

        # set info hash
        if self.info_hash:
            if self.info_hash != info_hash:
                raise UploadException('Torrent data info hash mismatch')
        else:
            self.info_hash = info_hash

        self.torrent_data = torrent_data
        self.torrent_info = torrent_info
        self.size = torrent_info.total_size()
        data_vol_root = config.get(MAIN_SECTION, 'data_volume_root')
        self.torrent_file = TorrentFile(torrent_data=torrent_data, torrent_root=data_vol_root)
        # need to relocate torrent file to have data and torrent in the same directory
        new_torrent_root = os.path.dirname(self.torrent_file.get_path()) + '/' + self.info_hash
        self.torrent_file.move(new_torrent_root)
        self.torrent_root = os.path.dirname(self.torrent_file.get_path())

    @staticmethod
    def find(info_hash):
        """
        Find upload by info hash.  Returns Upload object.
        """
        Upload._validate_info_hash(info_hash)
        data = upload_db.get(info_hash)
        upload = Upload._data_to_upload(data)
        return upload

    @staticmethod
    def _data_to_upload(data):
        if data:
            upload = Upload()
            upload.info_hash = data['info_hash']
            upload.size = data['size']
            upload.torrent_root = data['torrent_root']
            upload.finished = mongodb_db.mongo_to_bool(data['finished']),
            upload.date_created = data['date_created']
            upload.last_updated = data['last_updated']
            upload.torrent_file = Upload._get_torrent_file(upload)
        else:
            upload = None
        return upload

    @staticmethod
    def _get_torrent_file(upload):
        """
        Get TorrentFile instance for the upload torrent file.  Return None
        if there was an error or the torrent file is missing.
        """
        file_path = upload.torrent_root + '/' + upload.info_hash + '.torrent'
        try:
            tf = TorrentFile(filename=file_path, torrent_root=upload.torrent_root)
        except TorrentFileException:
            tf = None
        return tf

    def save(self):
        """ Persist upload to database """
        self.validate()
        if self.torrent_file and not self.torrent_file.exists():
            self.torrent_file.save()
        save_dict = self._get_save_dict()
        upload_db.save(save_dict)
        self.date_created = save_dict['date_created']
        self.last_updated = save_dict['last_updated']

    def validate(self):
        self._validate_info_hash(self.info_hash)
        if not self.torrent_root:
            raise UploadException('Missing torrent root')

    @staticmethod
    def _validate_info_hash(info_hash):
        if not info_hash:
            raise UploadException('Missing info hash')

        if not is_valid_info_hash(info_hash):
            raise UploadException('Invalid info hash')

    def _get_save_dict(self):
        date_created = self.date_created if self.date_created else self._get_now()
        last_updated = self.last_updated if self.last_updated else self._get_now()
        save_dict = {
            'info_hash': self.info_hash,
            'size': self.size,
            'torrent_root': self.torrent_root,
            'finished': mongodb_db.bool_to_mongo(self.finished),
            'date_created': date_created,
            'last_updated': last_updated
            }
        return save_dict

    def get_info(self):
        info = None
        if self.torrent_file:
            info = self.torrent_file.get_info()
        return info

    def delete(self, **kwargs):
        config = kwargs.get('config', None)
        if not config:
            raise UploadException('Missing config param')

        self._validate_info_hash(self.info_hash)
        if self.torrent_file and self.torrent_file.exists():
            self.torrent_file.delete()
            self.torrent_file = None

        # delete uploaded torrent data files
        shutil.rmtree(self.torrent_root)
        data_vol_root = config.get(MAIN_SECTION, 'data_volume_root')
        delete_empty_subdirs(data_vol_root, os.path.dirname(self.torrent_root))

        upload_db.delete(self.info_hash)
