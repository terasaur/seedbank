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
import time
import threading
import libtorrent as lt
from seedbank.server.alert_match import AlertMatch
import terasaur.log.log_helper as log_helper

class AlertWatcherException(Exception): pass

class AbstractAlertWatcher(object):
    def __init__(self, **kwargs):
        """
        Pull alerts from a libtorrent session alert queue and take
        appropriate action.  Uses an observer pattern with a list of
        AlertMatch objects that execute according to their matching
        and action behavior.

        :Parameters:
            - `label`: String used to identify the AlertWatcher instance
            - `session`: :class: libtorrent.session
            - `verbose`: :boolean:, enable detailed output for debugging
            - `match_list`: :list: of tuples containing a python class object
                referencing an :class:`AlertMatch` class and a dictionary of
                parameters for the object constructor.  :class:`AlertMatch`
                objects are created in the :class:`AlertWatcher` object because
                some match internals cannot cross process boundaries (e.g. socket
                connections).
            - `watch_loop_callback`: callback function that is called at
                the end of every watch loop iteration.
            - `loop_limit`: Force stop after the given number of watch loop
                iterations.  Useful for catching errors in automated tests.
            - `tick_interval`: Number of seconds to sleep between watch loop
                iterations.  Can be less than 1.  e.g. .001 == 1 millisecond
            - `purge_expired`: Remove expired match objects from the list.
                Necessary for long-running operation.

        Raises :class:`AlertWatcherException` if `label` is empty
        """
        self._label = kwargs.get('label', None)
        self._session = kwargs.get('session', None)
        self._verbose = bool(kwargs.get('verbose', False))
        self._match_list = {}
        self._match_all = bool(kwargs.get('match_all', True))
        self._watch_loop_callback = kwargs.get('watch_loop_callback', None)
        self._loop_limit = int(kwargs.get('loop_limit', 250))
        self._tick_interval = kwargs.get('tick_interval', 0.1)
        self._purge_expired = bool(kwargs.get('purge_expired', False))
        self._run = True
        self._log = log_helper.get_logger(self.__class__.__name__)
        self._log_all_alerts = False

        if kwargs.has_key('match_list'):
            self._add_match_items(kwargs['match_list'])

        if self._label:
            self._label = str(self._label)
        else:
            raise AlertWatcherException('Invalid AlertWatcher label')

        if not self._session:
            raise AlertWatcherException('Invalid libtorrent session')

    def _add_match_items(self, match_list):
        for param_tuple in match_list:
            self.add_match(param_tuple)

    def run(self):
        """
        Poll for alerts and attempt matching.  This function call blocks
        until one of the following conditions is met:
            - stop() is called
            - all match objects have expired (See AlertMatch for details)
            - the loop count limit is reached
        """
        idx = 0
        if self._verbose:
            self._log.info('(%s) Starting AlertWatcher' % self._label)
            self._log.debug('(%s) Sleep interval: %s' % (self._label, str(self._tick_interval)))
        while self._run:
            if self._loop_limit > 0 and idx >= self._loop_limit:
                if self._verbose:
                    self._log.info('(%s) Watch loop limit reached, exiting.' % self._label)
                break

            alerts = self._get_alerts(self._session)
            for alert in alerts:
                self._match_alert(alert)

            match_done = self.is_fully_matched()
            if match_done:
                if self._verbose:
                    self._log.info('(%s) Fully matched, exiting.' % self._label)
                break

            # TODO: purge expired here

            if self._watch_loop_callback is not None:
                self._watch_loop_callback()

            time.sleep(self._tick_interval)
            if self._loop_limit > 0:
                idx += 1

    def _match_alert(self, alert):
        if self._log_all_alerts:
            self._log.info('(%s) (%s) %s' % (self._label, alert.what(), alert.message()))
        for name, match_item in self._match_list.iteritems():
            matched = match_item.match(alert)
            if matched and not self._match_all:
                break

    def stop(self):
        self._log.info('(%s) Stopping' % self._label)
        if self._verbose:
            self._log.info('(%s) Stop signal received' % self._label)
        self._run = False

    def _get_alerts(self, ses):
        alerts = []
        alert = True
        while alert:
            alert = ses.pop_alert()
            self.__get_alerts_handle_alert(alerts, alert)
        return alerts

    def __get_alerts_handle_alert(self, alerts, alert):
        if not alert:
            return
        alerts.append(alert)
        if self._verbose:
            self._print_alert(alert)

    def _print_alert(self, alert):
        # stats alerts are too verbose
        if alert.what() == 'stats_alert':
            return
        self._log.info('(%s) (%s): %s' % (self._label, alert.what(), alert.message()))

    def is_fully_matched(self):
        match_done = True
        for name, m in self._match_list.iteritems():
            if not m.expired():
                match_done = False
                break
        return match_done

    def add_match(self, param_tuple):
        (name, klass, kwargs) = param_tuple
        if self._match_list.has_key(name):
            raise AlertWatcherException('Duplicate alert match name: %s' % name)

        match = klass(**kwargs)
        self._match_list[name] = match
        if self._verbose:
            self._log.info('(%s) Added new alert match item (%s: %s)' % (self._label, name, klass.__name__))

    def remove_match(self, name):
        if self._match_list.has_key(name):
            del self._match_list[name]

    def has_match(self, name):
        return self._match_list.has_key(name)

    def _clear_matches(self):
        self._match_list.clear()

class UnthreadedAlertWatcher(AbstractAlertWatcher):
    def start(self):
        """
        For Thread interface parity
        """
        self.run()

class ThreadedAlertWatcher(AbstractAlertWatcher, threading.Thread):
    """
    Threaded version of AlertWatcher.  Methods that can trigger state
    changes must invoke locking.
    """
    def __init__(self, **kwargs):
        self._alert_list_lock = threading.RLock()
        AbstractAlertWatcher.__init__(self, **kwargs)
        threading.Thread.__init__(self)

    def add_match(self, match):
        self._alert_list_lock.acquire()
        AbstractAlertWatcher.add_match(self, match)
        self._alert_list_lock.release()

    def _match_alert(self, alert):
        self._alert_list_lock.acquire()
        AbstractAlertWatcher._match_alert(self, alert)
        self._alert_list_lock.release()

    def remove_match(self, name):
        self._alert_list_lock.acquire()
        AbstractAlertWatcher.remove_match(self, name)
        self._alert_list_lock.release()

    def _clear_matches(self):
        self._alert_list_lock.acquire()
        AbstractAlertWatcher._clear_matches(self)
        self._alert_list_lock.release()
