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

import libtorrent as lt
import os

def decode_torrent_data(data):
    """
    Takes bencoded torrent file as a binary string and returns
    a libtorrent.torrent_info object.
    """
    decode = lt.bdecode(data)
    if not decode.has_key('info'):
        raise Exception('Invalid torrent data (missing info key)')
    if not decode['info'].has_key('pieces'):
        raise Exception('Invalid torrent data (missing pieces key)')
    return lt.torrent_info(decode)

def delete_empty_subdirs(root, path):
    """
    Recursively clean up empty subdirectories.  Be careful not to remove
    the root directory.
    """
    if path == root:
        return
    if os.listdir(path) == []:
        os.rmdir(path)
        delete_empty_subdirs(root, os.path.dirname(path))
