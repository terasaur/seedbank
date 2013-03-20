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
from seedbank.torrent.upload import Upload
from seedbank.torrent.torrent import Torrent
from seedbank.server.libtorrent_session import LibtorrentSessionQueueItem
from seedbank.cli.add_command import AddCommand
from seedbank.messaging.server_control_message import ServerUploadMessage
from terasaur.config.config_helper import MAIN_SECTION
import seedbank.server.shared as seedbank_shared

class UploadManagerException(Exception): pass

class UploadManager(object):
    SESSION_KEY_PREFIX = 'upload_'

    def __init__(self, **kwargs):
        self._config = kwargs.get('config', None)
        if not self._config:
            raise UploadManagerException('Missing config constructor param')
        self._verbose = kwargs.get('verbose', False)
        self._tick_interval = kwargs.get('tick_interval', 0.5)
        self._log = log_helper.get_logger(self.__class__.__name__)

        self._restart_unfinished()

    def _restart_unfinished(self):
        """
        Look for unfinished uploads after a server restart and
        reactivate the sessions.
        """
        pass

    def start(self, **kwargs):
        """
        Start an upload
        @param torrent_file

        Sequence of events:
          * Make sure the torrent isn't already seeded
          * Make sure an active upload session doesn't already exist
          * Create and start a libtorrent session client if one doesn't exist
          * Persist upload data to the database
          * Add the upload torrent to the client session
        """
        info_hash = kwargs.get('info_hash', None)
        torrent_file = kwargs.get('torrent_file', None)

        if not info_hash:
            raise UploadManagerException('Missing info hash data in start upload')

        if self._is_already_seeded(info_hash):
            return

        self._ensure_active_client_session()

        upload = self._get_upload(info_hash)
        if upload:
            self._start_existing(upload)
        else:
            self._start_new(info_hash, torrent_file)

    def _is_already_seeded(self, info_hash):
        t = Torrent.find(info_hash=info_hash)
        if t:
            self._log.info('Received upload request for a torrent that is already seeded (%s)' % info_hash)
            msg = ServerUploadMessage(upload_action='seeded',
                                      info_hash=info_hash,
                                      seedbank_id=self._config.get(MAIN_SECTION, 'terasaur_seedbank_id'),
                                      message='Torrent already exists in this seed bank')
            seedbank_shared.mq_out.publish(str(msg))
            seeded = True
        else:
            seeded = False
        return seeded

    def _start_new(self, info_hash, torrent_file):
        """
        * Validate the torrent file data
        * Create a directory for the torrent file and uploaded data
        """
        if not torrent_file:
            raise UploadManagerException('Missing torrent file data in start upload')
        if self._verbose:
            self._log.info('Creating new upload for %s' % info_hash)
        upload = Upload(info_hash=info_hash, torrent_data=torrent_file, config=self._config)
        upload.save()
        self._send_add_torrent_to_client(upload)

    def _start_existing(self, upload):
        if False:
            # If torrent is already active, just pause and restart it
            self._log.info('Found active client session for upload %s' % upload.info_hash)
            self._send_bump_torrent_to_client(upload.info_hash)
        self._send_add_torrent_to_client(upload)

    def _get_upload(self, info_hash):
        """
        Look for existing upload.  Return None if not found.
        """
        upload = Upload.find(info_hash)
        if upload:
            if self._verbose:
                self._log.info('Found existing upload for %s' % info_hash)
            # Trigger update of last updated timestamp
            upload.last_updated = None
            upload.save()
        return upload

    def stop(self, **kwargs):
        """
        Stop an active upload session
        @param info_hash
        """
        return

        info_hash = kwargs.get('info_hash', None)
        if not info_hash:
            raise UploadManagerException('Missing info hash data in stop upload')

        if not self._client_session_is_running():
            if self._verbose:
                self._log.info('Received stop upload for %s, but client session is stopped' % info_hash)
            return

        if self._verbose:
            self._log.info('Stopping upload session for %s' % info_hash)
        self._send_stop_torrent_to_client(info_hash)

    def cancel(self, **kwargs):
        """
        Cancel an upload.  Stops a session if active, deletes the torrent
        file and any data that was uploaded.
        @param info_hash
        """
        pass

    def delete(self, **kwargs):
        """
        Delete an uploaded torrent.  Stop if active, then delete the torrent
        file and any data that was uploaded.
        @param info_hash
        """
        info_hash = kwargs.get('info_hash')
        if not info_hash:
            self._log.error('Missing info hash trying to delete upload')
            return

        upload = Upload.find(info_hash)
        if not upload:
            self._log.error('Could not find upload for info hash: %s' % info_hash)
            return

        if not upload.finished:
            self.stop()

        torrent_root = self._config.get(MAIN_SECTION, 'torrent_file_root')
        torrent = Torrent.find(info_hash=info_hash, torrent_root=torrent_root)
        if torrent:
            self._log.info('Deleting torrent for completed upload: %s (%s)' % (torrent.name, info_hash))
            torrent.delete()

        self._log.info('Deleting upload for info hash: %s' % upload.info_hash)
        upload.delete(config=self._config)

        # Report back to terasaur
        msg = ServerUploadMessage(upload_action='deleted',
                                  info_hash=info_hash,
                                  seedbank_id=self._config.get(MAIN_SECTION, 'terasaur_seedbank_id'),
                                  message='Upload and data deleted')
        seedbank_shared.mq_out.publish(str(msg))

    def status(self, **kwargs):
        """
        Gets status information for an upload
        @param info_hash

        Responses:
            active: libtorrent client session running
            dormant: upload exists, but client session not running
            finished: data transfer complete
            seeded:

        """
        pass

    def convert_to_torrent(self, **kwargs):
        """
        Called when the seedbank server receives a torrent finished message
        from an upload client session.  Convert the upload into a seeded torrent
        and notify terasaur.
        @param info_hash
        @param torrent_path
        @param data_root
        """
        try:
            self._convert_to_torrent(**kwargs)
        except Exception, e:
            self._log.error(str(e))

    def _convert_to_torrent(self, **kwargs):
        info_hash = kwargs.get('info_hash', None)
        if not info_hash:
            raise UploadManagerException('Missing info_hash in UploadManager::handle_torrent_finished')

        if self._verbose:
            self._log.info('Received torrent finished message for %s' % info_hash)

        upload = Upload.find(info_hash)
        if not upload:
            raise UploadManagerException('Missing upload in UploadManager::handle_torrent_finished')

        if self._verbose:
            self._log.info('Found upload (%s)' % upload.torrent_root)
            self._log.info('Torrent file: %s' % upload.torrent_file.get_path())

        command = AddCommand(config=self._config,
                             torrent_file=upload.torrent_file.get_path(),
                             data_root=upload.torrent_root,
                             verbose=self._verbose,
                             quiet=(not self._verbose)
                             )
        command.execute()

        # Mark upload as finished
        upload.finished = True
        upload.last_updated = None
        upload.save()

        msg = ServerUploadMessage(upload_action='finished',
                                  info_hash=info_hash,
                                  seedbank_id=self._config.get(MAIN_SECTION, 'terasaur_seedbank_id'),
                                  message='Upload finished')
        seedbank_shared.mq_out.publish(str(msg))

        self._log.info('Converted upload to seeded torrent (%s)' % info_hash)


    """
    #----------------------------------------------------------------------#
    # Interactions with the SessionManager
    """
    def _ensure_active_client_session(self):
        if self._client_session_is_running():
            return

        # fork new libtorrent client process
        # TODO: does a libtorrent session have a root dir?
        session_params = {
            'session_type': 'client',
            'config': self._config,
            'tick_interval': self._tick_interval,
            'port': 0
            }
        self._log.info('Creating new client session for uploads')
        session_key = UploadManager.SESSION_KEY_PREFIX
        seedbank_shared.session_manager.create(session_key, **session_params)

    def _client_session_is_running(self):
        session_key = UploadManager.SESSION_KEY_PREFIX
        return seedbank_shared.session_manager.is_alive(session_key)

    def _send_bump_torrent_to_client(self, session_key, info_hash):
        params = {'info_hash': info_hash}
        self._send_to_session_manager('bump_torrent', params)

    def _send_add_torrent_to_client(self, upload):
        # send message to add torrent to libtorrent session
        tf = upload.torrent_file

        params = {
            'info_hash': upload.info_hash,
            'torrent_file': tf.get_data(),
            'torrent_root': upload.torrent_root
            }
        self._send_to_session_manager('add_torrent', params)

    def _send_stop_torrent_to_client(self, info_hash):
        params = {'info_hash': info_hash}
        self._send_to_session_manager('stop_torrent', params)

    def _send_to_session_manager(self, action, data):
        session_key = UploadManager.SESSION_KEY_PREFIX
        queue_item = LibtorrentSessionQueueItem(action, data)
        seedbank_shared.session_manager.send(session_key, queue_item)


    """
    # ***** implementation where each upload gets a separate forked libtorrent session

    session_key = UploadManager.SESSION_KEY_PREFIX + info_hash

    # Don't allow multiple libtorrent sessions for the same torrent
    if seedbank_shared.session_manager.is_alive(session_key):
        self._log.info('Found active client session for upload %s' % info_hash)
        self._send_bump_torrent_to_client(session_key, info_hash)
        return

    upload = self._get_or_create_upload(info_hash, torrent_file)
    self._create_client_session(session_key)
    self._send_add_torrent_to_client(session_key, upload)
    """
