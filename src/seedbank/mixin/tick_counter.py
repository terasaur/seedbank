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

class TickCounterMixin(object):
    def __init__(self, **kwargs):
        """
        Control timing of task execution from an event loop in another
        thread.

        :Parameters:
            - `exec_interval`: Number of seconds between task executions
            - `tick_interval`: Interval in seconds of the calling
                event loop.

        For example, to run a task every 5 seconds from a loop
        that ticks every 500 ms, set
            exec_interval=5, tick_interval=0.5
        """
        self._exec_interval = kwargs.get('exec_interval', 10)
        self._tick_interval = kwargs.get('tick_interval', 1.0)
        self._tick_counter_start = int(self._exec_interval/self._tick_interval) - 1

        if self._tick_counter_start < 1:
            raise ValueError('Tick counter out of bounds')
        self._reset_tick_counter()

    def _reset_tick_counter(self):
        self._tick_counter = self._tick_counter_start

    def tick(self, **kwargs):
        """
        Should be called from the containing object's event loop.
        """
        if self._tick_counter == 0:
            # reset tick counter first in case something below throws an exception
            self._reset_tick_counter()
            self._tick(**kwargs)
        else:
            self._tick_counter -= 1

    def _tick(self, **kwargs):
        raise NotImplementedError('Must override TickCounterMixin::_tick')
