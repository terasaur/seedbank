#!/usr/bin/env python2.6
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
import os
import traceback
from optparse import OptionParser, OptionGroup

# Path adjustment for non-dev deployments
local_libdir = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + '/../lib')
if os.path.exists(local_libdir):
    sys.path.insert(0, local_libdir)

# Add upstream/vendor libraries path for dev deployments
upstream_libdir = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + '/../upstream')
if os.path.exists(upstream_libdir):
    sys.path.insert(0, upstream_libdir)

import seedbank.config.config_defaults as config_defaults
import terasaur.config.config_helper as config_helper
from seedbank.cli.seedbank_cli import SeedbankCLI
import terasaur.log.log_helper as log_helper

_LOGGER_NAME = 'seedbank'

def _get_option_parser():
    usage = """%prog [options] <command> <files>

Available commands:
    add             Add a torrent
    remove          Remove a torrent
    list            List torrents
    create          Create new torrent
    upload          Upload torrent file to terasaur
    stats           Start, stop, or monitor seedbank stats
    sync            Sync terasaur status with local torrent availability
    offline         Notify terasaur, mark all torrents as offline"""

    parser = OptionParser(usage=usage,
                          version='%prog 1.0',
                          description='Seedbank controller CLI')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='Enable verbose output')
    parser.add_option('--debug', action='store_true', dest='debug', default=False, help='Enable debug output')

    multi_group = OptionGroup(parser, 'Multi-command options', '')
    multi_group.add_option('--torrent', dest='torrent_file', type='string', metavar="PATH", help='Torrent file (input or output as appropriate)', default=None)
    multi_group.add_option('--info_hash', dest='info_hash', type='string', metavar="SHA1", help='Specify info hash', default=None)
    multi_group.add_option('--start', dest='start', action='store_true', help='Start, applies to stats and uploads', default=False)
    multi_group.add_option('--stop', dest='stop', action='store_true', help='Stop, applies to stats and uploads', default=False)
    parser.add_option_group(multi_group)

    add_group = OptionGroup(parser, 'Add options', '')
    add_group.add_option('--root', dest='data_root', type='string', metavar="PATH", help='Specify directory that contains torrent contents', default=None)
    parser.add_option_group(add_group)

    create_group = OptionGroup(parser, 'Create options', '')
    create_group.add_option('--data', dest='torrent_data', type='string', metavar="PATH", help='Specify file or directory for torrent contents', default=None)
    create_group.add_option('--tracker', dest='tracker', type='string', help='Tracker announce URL (e.g. http://tracker.example.org:6969/announce', default=None)
    create_group.add_option('--overwrite', dest='overwrite', action='store_true', help='Overwrite output torrent file if exists', default=False)
    create_group.add_option('--progress', dest='progress', action='store_true', help='Show progress information', default=True)
    create_group.add_option('--comment', dest='comment', type='string', metavar="COMMENT", help='Comment for torrent file', default=None)
    parser.add_option_group(create_group)

    upload_group = OptionGroup(parser, 'Upload options', '')
    upload_group.add_option('--itemid', dest='item_id', type='string', metavar="ID", help='Terasaur item id for torrent publication', default=None)
    parser.add_option_group(upload_group)

    stats_group = OptionGroup(parser, 'Stats options', '')
    stats_group.add_option('--watch', dest='stats_watch', action='store_true', help='Read and print stats messages', default=False)
    stats_group.add_option('--setup', dest='stats_setup', action='store_true', help='Run setup tasks on rabbitmq exchange (dev/test only)', default=False)
    parser.add_option_group(stats_group)

    return parser

def _parse_args():
    parser = _get_option_parser()
    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_usage()
        options = None
        args = None

    return (parser, options, args)

def main():
    (parser, options, args) = _parse_args()
    if options is None:
        return

    if options.start and options.stop:
        parser.error("Cannot perform start and stop operations at the same time")

    # nasty hack
    log_helper._LOG_NAME = _LOGGER_NAME

    try:
        config_defaults.init()
        ch = config_helper.ConfigHelper()
        config = ch.get_config()
        cli = SeedbankCLI(config)
        cli.execute(options, args)
    except Exception, e:
        print 'ERROR: ' + str(e)
        if options.debug is True:
            traceback.print_exc()

if __name__ == '__main__':
    main()
