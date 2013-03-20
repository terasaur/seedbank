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

import bson

class ServerControlMessage(object):
    def __init__(self):
        self._dict = None

    def __str__(self):
        return bson.BSON().encode(self._dict)

class ServerInitMessage(ServerControlMessage):
    # TODO: generate a unique seedbank id, store in mongodb
    def __init__(self, **kwargs):
        self._dict = {'action': 'seedbank_init',
                      'seedbank_id': kwargs.get('seedbank_id', ''),
                      'peer_id': kwargs.get('peer_id', '')}

class ServerUploadMessage(ServerControlMessage):
    def __init__(self, **kwargs):
        self._dict = {'action': 'upload',
                      'upload_action': kwargs.get('upload_action', ''),
                      'info_hash': kwargs.get('info_hash', ''),
                      'message': kwargs.get('message', '')
                      }

class ServerPingRequestMessage(ServerControlMessage):
    def __init__(self, **kwargs):
        self._dict = {'action': 'ping_request',
                      'correlation_id': kwargs.get('correlation_id', ''),
                      'reply_to': kwargs.get('reply_to', '')}

class ServerPingResponseMessage(ServerControlMessage):
    def __init__(self, **kwargs):
        self._dict = {'action': 'ping_response',
                      'correlation_id': kwargs.get('correlation_id', '')}
