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

"""
Collections of libtorrent session settings
"""

def get_client_settings():
    set = _get_basic_settings()
    set.enable_outgoing_utp = True
    return set

def get_server_settings():
    set = _get_basic_settings()
    _apply_high_perf_seed_settings(set)

    # Required for a new request to trigger a mongodb lookup
    set.incoming_starts_queued_torrents = True

    # Setting no_atime_storage to True causes errors when serving files
    # from a read-only filesystem.
    set.no_atime_storage = False

    set.enable_incoming_utp = True
    set.enable_outgoing_utp = True

    # cache_size is the number of 16 K blocks.  Calculate setting from
    # the desired cache size in KB.
    set.cache_size = (262144/16)

    # the number of blocks that will be read ahead when reading a block
    # into the read cache.  Setting this value to 1 will make the storage
    # layer responsible for performance.
    set.read_cache_line_size = 1

    return set

def _get_basic_settings():
    set = lt.session_settings()
    set.user_agent = 'terasaur/'
    set.seeding_outgoing_connections = False
    return set

def _apply_high_perf_seed_settings(set):
    # setting from high_performance_seed()
    set.mixed_mode_algorithm = lt.bandwidth_mixed_algo_t.prefer_tcp
    set.alert_queue_size = 10000
    set.file_pool_size = 500
    set.no_atime_storage = True
    set.allow_multiple_connections_per_ip = True
    set.connection_speed = 500
    set.connections_limit = 8000
    set.listen_queue_size = 200
    set.unchoke_slots_limit = 500
    set.dht_upload_rate_limit = 100000
    set.read_job_every = 100
    set.cache_size = 32768 * 2
    set.use_read_cache = True
    set.cache_buffer_chunk_size = 128
    set.read_cache_line_size = 32
    set.write_cache_line_size = 32
    set.low_prio_disk = False
    set.cache_expiry = 60 * 60
    set.lock_disk_cache = False
    set.max_queued_disk_bytes = 10 * 1024 * 1024
    #set.disk_cache_algorithm = session_settings.avoid_readback
    set.explicit_read_cache = False
    set.allowed_fast_set_size = 0
    set.suggest_mode = 1 # session_settings::suggest_read_cache == 1
    set.close_redundant_connections = True
    set.max_rejects = 10
    set.optimize_hashing_for_speed = True
    set.request_timeout = 10
    set.peer_timeout = 20
    set.inactivity_timeout = 20
    set.active_limit = 2000
    set.active_tracker_limit = 2000
    set.active_dht_limit = 600
    set.active_seeds = 2000
    set.choking_algorithm = lt.choking_algorithm_t.fixed_slots_choker
    set.send_buffer_watermark = 10 * 1024 * 1024
    set.send_buffer_watermark_factor = 10
    set.max_failcount = 1
    set.utp_dynamic_sock_buf = True
