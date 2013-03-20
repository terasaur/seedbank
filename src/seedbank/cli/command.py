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

import sys
import terasaur.log.log_helper as log_helper

class CommandException(Exception): pass

class Command(object):
    """
    Abstract command
    """
    ADD = 'add'
    REMOVE = 'remove'
    LIST = 'list'
    CREATE = 'create'
    UPLOAD = 'upload'
    STATS = 'stats'
    SYNC = 'sync'
    OFFLINE = 'offline'

    def __init__(self, **kwargs):
        self._config = kwargs.get('config', None) # ConfigParser
        self._quiet = kwargs.get('quiet', False)
        self._init_log()

    def _print(self, s):
        if not self._quiet:
            sys.stdout.write(s)
            sys.stdout.flush()

    def _println(self, s):
        self._print(s + "\n")

    def _init_log(self):
        log_type = log_helper.LOG_TYPE_STREAM
        log_level = 'info'
        log_target = sys.stdout
        log_helper.initialize(log_type, log_level, log_target)
