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

import time
import traceback

from terasaur.log.log_init import LogInitMixin
from terasaur.config.config_helper import MAIN_SECTION, MQ_SECTION
from terasaur.messaging.rabbitmq_consumer import RabbitMQConsumer
from seedbank.messaging.server_control_handler import SeedbankControlMessageHandler
from terasaur.messaging.rabbitmq_publisher import SelfManagingRabbitMQPublisher
from seedbank.messaging.server_control_message import ServerInitMessage
from terasaur.messaging.rabbitmq_connector import CONTENT_TYPE_BINARY
from terasaur.db import mongodb_db, torrent_db
from seedbank.db import upload_db
from seedbank.server.session_manager import SessionManager
from seedbank.server.upload_manager import UploadManager
import seedbank.server.shared as seedbank_shared

class SeedbankServerException(Exception): pass

class SeedbankServer(LogInitMixin):
    def __init__(self, **kwargs):
        self.__init_from_kwargs(**kwargs)
        self._tick_interval = 0.5
        self._log = None

    def __init_from_kwargs(self, **kwargs):
        self._config_helper = kwargs.get('config_helper', None)
        self._verbose = bool(kwargs.get('verbose', False))
        self._debug = bool(kwargs.get('debug', False))
        self._forked = bool(kwargs.get('fork', False))

        if not self._config_helper:
            raise SeedbankServerException('Missing config helper')

    def start(self):
        config = self._get_config()
        self._init_log(config)
        self._init_seedbank_db(config)
        seedbank_shared.session_manager = SessionManager(config=config, verbose=self._verbose, debug=self._debug)
        seedbank_shared.session_manager.create('server', session_type='server', config=config, tick_interval=self._tick_interval)
        seedbank_shared.upload_manager = UploadManager(config=config, verbose=self._verbose)
        self._start_mq_connectors()

        try:
            while seedbank_shared.session_manager.is_alive('server'):
                try:
                    self._handle_session_queues()
                    seedbank_shared.session_manager.tick()
                except Exception, e:
                    if self._verbose:
                        traceback.print_exc()
                    self._log.error(str(e))
                time.sleep(self._tick_interval)

        except KeyboardInterrupt:
            pass

        self._stop_mq_connectors()
        seedbank_shared.session_manager.join()
        self._log.info('Exiting...')

    def stop(self):
        self._log.info('Stopping')
        seedbank_shared.session_manager.stop()

    def _get_config(self):
        return self._config_helper.get_config()

    def _init_log(self, config):
        LogInitMixin.__init__(self, config=config)

    def _init_seedbank_db(self, config):
        mongodb_db.set_connection_params_from_config(config)
        torrent_db.initialize()
        upload_db.initialize()

    def _handle_session_queues(self):
        queue_items = seedbank_shared.session_manager.check_queues()
        for item in queue_items:
            if item.type == 'torrent_finished':
                seedbank_shared.upload_manager.convert_to_torrent(info_hash=item.value['info_hash'])
            if item.type == 'server_init':
                config = self._get_config()
                msg = ServerInitMessage(seedbank_id=config.get(MAIN_SECTION, 'terasaur_seedbank_id'), peer_id=item.value['peer_id'])
                seedbank_shared.mq_out.publish(str(msg))

    """
    Message queue functions
    """
    def _start_mq_connectors(self):
        """ Start rabbitmq connections """
        config = self._get_config()
        self._start_mq_out(config)
        self._start_mq_in(config)

    def _stop_mq_connectors(self):
        """ Stop rabbitmq connections """
        self._stop_mq_in(seedbank_shared.mq_in)
        self._stop_mq_out(seedbank_shared.mq_out)

    def _start_mq_in(self, config):
        """
        Initiate inbound consumer connection to rabbitmq
        """
        queue_name = config.get(MQ_SECTION, 'control_queue')
        handler = SeedbankControlMessageHandler(server=self, verbose=self._verbose)
        seedbank_shared.mq_in = RabbitMQConsumer(config=config,
                                       handler=handler,
                                       queue_name=queue_name,
                                       verbose=self._verbose,
                                       debug=self._debug)
        seedbank_shared.mq_in.start()

    def _start_mq_out(self, config):
        """
        Initiate outbound publisher connection to rabbitmq
        """
        routing_key = config.get(MQ_SECTION, 'terasaur_queue')
        seedbank_shared.mq_out = SelfManagingRabbitMQPublisher(config=config,
                                                     routing_key=routing_key,
                                                     content_type=CONTENT_TYPE_BINARY,
                                                     verbose=self._verbose,
                                                     debug=self._debug)

    def _stop_mq_in(self, mq_in):
        if self._debug:
            self._log.info('Calling mq_in::stop')
        seedbank_shared.mq_in.stop()
        if self._debug:
            self._log.info('Calling mq_in::join')
        mq_in.join()
        mq_in = None

    def _stop_mq_out(self, mq_out):
        if self._debug:
            self._log.info('Calling mq_out::stop')
        mq_out.stop()
        mq_out = None
