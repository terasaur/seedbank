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

"""
Container for sharing references between classes in the server process
"""

#import threading
#_LOCK = threading.Semaphore()

# RabbitMQ inbound and outbound queues
mq_in = None
mq_out = None

# SessionManager, libtorrent session processes
session_manager = None

# UploadManager, upload torrents into seed bank
upload_manager = None
