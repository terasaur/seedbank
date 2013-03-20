#
# Copyright 2013 ibiblio
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

import os.path
import libtorrent as lt
from seedbank.cli.command import Command, CommandException
import terasaur.config.config_helper as config_helper
from seedbank.cli.message_publisher_mixin import MessagePublisherMixin

class UploadCommand(Command, MessagePublisherMixin):
    """
    Send start or stop upload message to seedbank.  Currently does not
    support initiating a new upload.
    """

    _ACTION = 'upload'

    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)
        self._info_hash = kwargs.get('info_hash', '')
        self._verbose = kwargs.get('verbose', False)
        self._set_upload_action(**kwargs)

    def _set_upload_action(self, **kwargs):
        if kwargs.get('start') is True:
            self._upload_action = 'start'
        elif kwargs.get('stop') is True:
            self._upload_action = 'stop'
        else:
            raise CommandException('Could not determine upload action')

    def execute(self):
        try:
            self._assert_required_params()

            mq = self.create_seedbank_publisher()
            message_dict = {
                'action': UploadCommand._ACTION,
                'upload_action': self._upload_action,
                'info_hash': self._info_hash
                }
            mq.publish(self.encode_message(message_dict))
            mq.stop()
        except CommandException, e:
            self._println('Error: ' + str(e))


    def _assert_required_params(self):
        if not (self._info_hash):
            raise CommandException('Must provide an info hash')
        #if not (self._torrent_file or self._info_hash):
        #    raise CommandException('Must provide either a torrent filename or an info hash')

    """
    save this to allow creating a new upload from a torrent file

    'filename': os.path.basename(self._torrent_file),
    'torrent': bson.binary.Binary(data)

    def _create_upload(self):
        data = self._get_data_from_file(self._torrent_file)
    """


