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
import bson

from seedbank.cli.command import Command, CommandException
from terasaur.messaging.rabbitmq_consumer import RabbitMQConsumer
from terasaur.messaging.rabbitmq_administrator import RabbitMQAdministrator
import terasaur.config.config_helper as config_helper
from seedbank.cli.message_publisher_mixin import MessagePublisherMixin

class TorrentStatsMessagePrinter(object):
    def handle(self, message):
        print message.body

    def _deserialize_message(self, message):
        data = bson.BSON.decode(message)
        return data

class StatsCommand(Command, MessagePublisherMixin):
    def __init__(self, **kwargs):
        Command.__init__(self, **kwargs)
        self._connector = None
        self._start = kwargs.get('start', False)
        self._stop = kwargs.get('stop', False)
        self._watch = kwargs.get('watch', False)
        self._setup = kwargs.get('setup', False)
        self._verbose = kwargs.get('verbose', False)
        self._consumer_klass = RabbitMQConsumer

    def execute(self):
        if not self._config:
            raise CommandException('Missing config')

        if self._start and self._stop:
            raise CommandException('Cannot start and stop at the same time')
        if self._start or self._stop:
            message_data = {'action':'publish_stats', 'enable':self._start}
            message = self.encode_message(message_data)
            self._send_publish_stats_message(message)

        if self._watch:
            self._watch_queue()

        if self._setup:
            self._declare_exchange()

    def _watch_queue(self):
        self._connector = self._create_stats_consumer()
        self._connector.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        self._connector.stop()
        self._connector.join()

    def _create_stats_consumer(self):
        queue_name = self._config.get(config_helper.MQ_SECTION, 'stats_queue')
        handler = TorrentStatsMessagePrinter()
        mq = self._consumer_klass(config=self._config,
                                  handler=handler,
                                  queue_name=queue_name,
                                  verbose=self._verbose)
        return mq

    def _send_publish_stats_message(self, message):
        mq = self.create_control_publisher()
        mq.publish(message)
        mq.stop()

    def _declare_exchange(self):
        mq = RabbitMQAdministrator(config=self._config,
                                   verbose=self._verbose)
        mq.start()
        idx = 0
        stop = 5
        while not mq.connected() and idx < stop:
            #self._println('Waiting for MQ tasks to finish')
            idx += 1
            time.sleep(1)
        mq.stop()
