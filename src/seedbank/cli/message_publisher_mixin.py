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

import terasaur.config.config_helper as config_helper
from terasaur.messaging.rabbitmq_publisher import SelfManagingRabbitMQPublisher
import bson

class MessagePublisherMixin(object):
    _PUBLISHER_KLASS = SelfManagingRabbitMQPublisher

    def create_terasaur_publisher(self):
        """
        Returns publisher for sending messages to the terasaur web app control queue
        """
        routing_key = self._config.get(config_helper.MQ_SECTION, 'terasaur_queue')
        return self._create_publisher(routing_key)

    def create_seedbank_publisher(self):
        """
        Returns publisher for sending messages to the seedbank control queue
        """
        routing_key = self._config.get(config_helper.MQ_SECTION, 'control_queue')
        return self._create_publisher(routing_key)

    def encode_message(self, data):
        encoder = bson.BSON()
        return encoder.encode(data)

    def _create_publisher(self, routing_key):
        if self._verbose:
            self._println('Creating publisher for queue ' + routing_key)
        mq = MessagePublisherMixin._PUBLISHER_KLASS(config=self._config,
                                   routing_key=routing_key,
                                   verbose=self._verbose)
        return mq
