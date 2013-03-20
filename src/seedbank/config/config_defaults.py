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
import terasaur.config.config_helper as config_helper
import terasaur.db.mongodb_db as mongodb_db

"""
Default list when looking for a configuration file.  The first match
is read by the ConfigHelper.
"""
CONFIG_FILENAME = 'seedbank.conf'
CONFIG_SEARCH_DEFAULT = [
    CONFIG_FILENAME,
    'conf/' + CONFIG_FILENAME,
    os.path.dirname(__file__) + '/../../../conf/' + CONFIG_FILENAME,
    '/usr/local/seedbank/conf/' + CONFIG_FILENAME,
    '/etc/seedbank/' + CONFIG_FILENAME
    ]

UPLOAD_SECTION = 'upload'
CREATE_TORRENT_SECTION = 'create_torrent'

"""
Default configuration values
"""
DEFAULT_VALUES = {
    config_helper.MAIN_SECTION: {
        'torrent_file_root': '/var/lib/seedbank/torrents',
        'listen_address': '0.0.0.0',
        'listen_port': '6881',
        'error_log': '/var/log/seedbank/error.log',
        'log_level': 'info',
        'inactive_torrent_timeout': 60,
        'torrent_manager_exec_interval': 5,
        'data_volume_root': '/var/lib/seedbank/data'
        },
    UPLOAD_SECTION: {
            'allow_upload': False,
            'upload_port_min': 6882,
            'upload_port_max': 6900,
            'torrent_timeout': 300
        },
    config_helper.MONGODB_SECTION: {
        'db_host': 'localhost',
        'db_port': '27017',
        'db_name': 'seedbank',
        'db_user': '',
        'db_pass': ''
        },
    config_helper.MQ_SECTION: {
        'host': 'localhost',
        'port': '5672',
        'user': 'terasaur',
        'pass': 'terasaur',
        'vhost': '/terasaur',
        'exchange': 'terasaur',
        'control_queue': 'seedbank.control',
        'stats_queue': 'seedbank.stats',
        'terasaur_queue': 'terasaur.web'
        },
    CREATE_TORRENT_SECTION: {
        'tracker_url': 'http://tracker.ibiblio.org/announce'
        }
    }

def init():
    global DEFAULT_VALUES
    global CONFIG_SEARCH_DEFAULT
    config_helper.set_defaults(DEFAULT_VALUES, CONFIG_SEARCH_DEFAULT)
    mongodb_db.reset_config_values(DEFAULT_VALUES)
