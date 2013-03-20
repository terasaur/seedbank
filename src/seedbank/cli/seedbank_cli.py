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

import copy
import terasaur.db.mongodb_db as mongodb_db
from seedbank.cli.command import Command, CommandException
from seedbank.cli.add_command import AddCommand
from seedbank.cli.remove_command import RemoveCommand
from seedbank.cli.list_command import ListCommand
from seedbank.cli.create_command import CreateCommand
from seedbank.cli.upload_command import UploadCommand
from seedbank.cli.stats_command import StatsCommand
from seedbank.cli.sync_command import SyncCommand
from seedbank.cli.offline_command import OfflineCommand

class SeedbankCLIException(Exception): pass

class SeedbankCLI(object):
    def __init__(self, config):
        if not config:
            raise SeedbankCLIException('Missing ConfigParser')
        self._config = config

    def execute(self, options, args):
        args_copy = copy.deepcopy(args)
        self._execute_command(options, args_copy)

    def _execute_command(self, options, args):
        command_str = args.pop(0)
        if command_str == Command.ADD:
            self._add(options, args)
        elif command_str == Command.REMOVE:
            self._remove(options, args)
        elif command_str == Command.CREATE:
            self._create(options, args)
        elif command_str == Command.UPLOAD:
            self._upload(options, args)
        elif command_str == Command.STATS:
            self._stats(options, args)
        else:
            command = self._create_command(command_str,
                                           config=self._config,
                                           verbose=options.verbose)
            command.execute()

    def _create_command(self, type, **kwargs):
        if type == Command.ADD:
            command = AddCommand(**kwargs)
        elif type == Command.REMOVE:
            command = RemoveCommand(**kwargs)
        elif type == Command.LIST:
            command = ListCommand(**kwargs)
        elif type == Command.CREATE:
            command = CreateCommand(**kwargs)
        elif type == Command.UPLOAD:
            command = UploadCommand(**kwargs)
        elif type == Command.STATS:
            command = StatsCommand(**kwargs)
        elif type == Command.SYNC:
            command = SyncCommand(**kwargs)
        elif type == Command.OFFLINE:
            command = OfflineCommand(**kwargs)
        else:
            raise CommandException('Invalid command: ' + type)
        return command

    def _add(self, options, args):
        self._init_seedbank_db()
        torrent_file = options.torrent_file
        data_root = options.data_root
        #torrent_root = options.torrent_root
        command = self._create_command(Command.ADD,
                                       config=self._config,
                                       torrent_file=torrent_file,
                                       data_root=data_root,
                                       verbose=options.verbose
                                       )
        command.execute()

    def _remove(self, options, args):
        self._init_seedbank_db()
        info_hash = options.info_hash
        command = self._create_command(Command.REMOVE,
                                       config=self._config,
                                       info_hash=info_hash,
                                       verbose=options.verbose
                                       )
        command.execute()

    def _init_seedbank_db(self):
        mongodb_db.set_connection_params_from_config(self._config)

    def _create(self, options, args):
        command = self._create_command(Command.CREATE,
                                       config=self._config,
                                       torrent_data=options.torrent_data,
                                       output_file=options.torrent_file,
                                       tracker=options.tracker,
                                       overwrite=options.overwrite,
                                       show_progress=options.progress,
                                       comment=options.comment,
                                       verbose=options.verbose
                                       )
        command.execute()

    def _upload(self, options, args):
        command = self._create_command(Command.UPLOAD,
                                       config=self._config,
                                       torrent_file=options.torrent_file,
                                       info_hash=options.info_hash,
                                       start=options.start,
                                       stop=options.stop,
                                       verbose=options.verbose
                                       )
        command.execute()

    def _stats(self, options, args):
        command = self._create_command(Command.STATS,
                                       config=self._config,
                                       start=options.start,
                                       stop=options.stop,
                                       watch=options.stats_watch,
                                       setup=options.stats_setup,
                                       verbose=options.verbose
                                       )
        command.execute()

    def _out(self, msg):
        print msg
