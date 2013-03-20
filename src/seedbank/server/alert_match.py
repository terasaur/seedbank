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

import terasaur.log.log_helper as log_helper

class AlertMatchException(Exception): pass

class AlertMatch(object):
    """
    Abstract class.  Do not instantiate directly.
    """
    def __init__(self, **kwargs):
        self._type = None
        self._message = None
        self._verbose = False
        self._match_count = 0
        self._expires_after = 1
        self._log_on_match = False
        self._log = log_helper.get_logger(self.__class__.__name__)
        self.__init_from_kwargs(**kwargs)

        if not self._type:
            raise AlertMatchException('Invalid AlertMatch type')

    def __init_from_kwargs(self, **kwargs):
        if kwargs.has_key('type') and kwargs['type'] is not None:
            self._type = str(kwargs['type'])
        if kwargs.has_key('message') and kwargs['message'] is not None:
            self._message = str(kwargs['message'])
        if kwargs.has_key('verbose'):
            self._verbose = bool(kwargs['verbose'])
        if kwargs.has_key('expires_after'):
            self._expires_after = int(kwargs['expires_after'])
        if kwargs.has_key('log_on_match'):
            self._log_on_match = bool(kwargs['log_on_match'])

    def match(self, alert):
        """
        Attempt match for given alert.  Returns True if matched, false
        otherwise.  Successful match also increments the match counter.

        Alert type must always match.  Alert message is only matched if
        a message is set in the match object.
        """
        if not alert:
            raise AlertMatchException('Got null alert in AlertMatch::match')

        matched = self._is_match(alert)
        if matched:
            if not self.expired():
                self._on_match(alert)
            self._match_count += 1
        return matched

    def _is_match(self, alert):
        matched = True
        if self._is_type_match(alert):
            if self._message and not self._is_message_match(alert):
                matched = False
        else:
            matched = False
        return matched

    def _on_match(self, alert):
        """
        Override to trigger events when an alert is matched.
        Called when:
            - an alert is matched
            - the match object is not expired
        """
        if self._log_on_match:
            self._log.info(self._get_alert_string(alert))

    def _get_alert_string(self, alert):
        """
        String used for printing or logging alerts
        """
        s = '(%s) %s' % (alert.what(), alert.message())
        return s

    def expired(self):
        if self._expires_after > 0 and self._match_count >= self._expires_after:
            return True
        else:
            return False

    def _is_type_match(self, alert):
        what = alert.what()
        if str(what) == self._type:
            return True
        else:
            if self._verbose:
                self._log.info('***** Type mismatch: ' + what + ' != ' + self._type)
            return False

    def _is_message_match(self, alert):
        msg = alert.message()
        if msg == self._message:
            return True
        else:
            if self._verbose:
                self._log.info('***** Message mismatch')
                self._log.info('Message: ]' + msg + '[')
                self._log.info('Expected: ]' + self._message + '[')
            return False

    def __str__(self):
        s = 'AlertMatch: %s: %s' % (self._type, self._message)
        return s

class MongodbAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'mongodb_plugin_alert'

        self.code = kwargs.get('code', '')
        if kwargs.has_key('msg'):
            kwargs['message'] = '(%i) %s' % (self.code, kwargs['msg'])
        AlertMatch.__init__(self, **kwargs)

class TorrentFinishedAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'torrent_finished_alert'
        if kwargs.has_key('torrent'):
            kwargs['message'] = '%s torrent finished downloading' % (kwargs['torrent'])
        AlertMatch.__init__(self, **kwargs)

class ListenSucceededAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'listen_succeeded_alert'
        if kwargs.has_key('ip_address') and kwargs.has_key('port'):
            kwargs['message'] = 'successfully listening on %s:%i' % (kwargs['ip_address'], kwargs['port'])
        AlertMatch.__init__(self, **kwargs)

class ListenFailedAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'listen_failed_alert'
        AlertMatch.__init__(self, **kwargs)

class IncomingConnectionAlertMatch(AlertMatch):
    _SOCKET_TYPE_LIST =[
        "null",
        "TCP",
        "Socks5/TCP",
        "HTTP",
        "uTP",
        "i2p",
        "SSL/TCP",
        "SSL/Socks5",
        "HTTPS",
        "SSL/uTP"
        ]

    def __init__(self, **kwargs):
        kwargs['type'] = 'incoming_connection_alert'
        message = self.__get_message(**kwargs)
        if message is not None:
            kwargs['message'] = message
        AlertMatch.__init__(self, **kwargs)

    def __get_message(self, **kwargs):
        if not (kwargs.has_key('ip_address') and kwargs.has_key('port') and kwargs.has_key('socket_type')):
            return None
        socket_type_str = IncomingConnectionAlertMatch._SOCKET_TYPE_LIST[kwargs['socket_type']]
        message = 'incoming connection from %s:%u (%s)' % (kwargs['ip_address'], kwargs['port'], socket_type_str)
        return message

class PeerConnectAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'peer_connect_alert'
        message = self.__get_message(**kwargs)
        if message is not None:
            kwargs['message'] = message
        AlertMatch.__init__(self, **kwargs)

    def __get_message(self, **kwargs):
        if not kwargs.has_key('ip_address'):
            return None

        client = kwargs.get('client', 'Unknown')
        message = 'peer (%s, %s) connecting to peer' % (kwargs['ip_address'], client)
        if kwargs.has_key('torrent'):
            message = kwargs['torrent'] + ' ' + message
        else:
            message = ' -  ' + message
        return message

class PeerDisconnectedAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'peer_disconnected_alert'
        message = self.__get_message(**kwargs)
        if message is not None:
            kwargs['message'] = message
        AlertMatch.__init__(self, **kwargs)

    def __get_message(self, **kwargs):
        if not (kwargs.has_key('ip_address') and kwargs.has_key('reason')):
            return None

        client = kwargs.get('client', 'Unknown')
        message = 'peer (%s, %s) disconnecting: %s' % (kwargs['ip_address'], client, kwargs['reason'])
        if kwargs.has_key('torrent'):
            message = kwargs['torrent'] + ' ' + message
        else:
            message = ' -  ' + message
        return message

class FileErrorAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'file_error_alert'
        message = self.__get_message(**kwargs)
        if message is not None:
            kwargs['message'] = message
        AlertMatch.__init__(self, **kwargs)

    def __get_message(self, **kwargs):
        if not (kwargs.has_key('filename') and kwargs.has_key('filepath')):
            return None

        if kwargs.has_key('error'):
            error = kwargs['error']
        else:
            error = 'No such file or directory'
        message = '%s file (%s) error: %s' % (kwargs['filename'], kwargs['filepath'], error)
        return message

class TorrentErrorAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'torrent_error_alert'
        if kwargs.has_key('torrent') and kwargs.has_key('error'):
            kwargs['message'] = '%s ERROR: %s' % (kwargs['torrent'], kwargs['error'])
        AlertMatch.__init__(self, **kwargs)

class TorrentStatsAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'stats_alert'
        AlertMatch.__init__(self, **kwargs)

    def _get_alert_string(self, alert):
        s = '(%s) %s %s' % (alert.what(), alert.handle.info_hash(), alert.message())
        return s

class TrackerErrorAlertMatch(AlertMatch):
    def __init__(self, **kwargs):
        kwargs['type'] = 'tracker_error_alert'
        AlertMatch.__init__(self, **kwargs)

    def _get_alert_string(self, alert):
        s = '(%s) %s %s' % (alert.what(), alert.message(), alert.error.message())
        return s


