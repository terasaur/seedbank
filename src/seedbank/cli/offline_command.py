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

from seedbank.cli.command import Command, CommandException

class OfflineCommand(Command):
    def execute(self):
        self._conn = None # placeholder
        self._conn.login()
        self._print('Unlinking all torrents\n')
        self._conn.get_conn().unlinkAll()
        self._conn.logout()
