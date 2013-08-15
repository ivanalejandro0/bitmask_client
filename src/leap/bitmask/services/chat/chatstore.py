# -*- coding: utf-8 -*-
# chatstore.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Store class, interface to save and retrieve chat logs from/to Soledad.
"""
import logging
import json
import ssl

from PySide import QtCore

from twisted.python import log
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from leap.common.check import leap_assert, leap_assert_type
from leap.soledad import Soledad
from leap.keymanager.openpgp import OpenPGPKey
from leap.keymanager.errors import KeyNotFound

logger = logging.getLogger(__name__)


class ChatStore(QtCore.QObject):
    """
    Loads/saves history logs from/to Soledad.
    """

    ENC_SCHEME_KEY = "_enc_scheme"
    ENC_JSON_KEY = "_enc_json"
    chat_logs_ready = QtCore.Signal()

    def __init__(self, keymanager, soledad):
        """
        Initialize ChatLogger.

        :param keymanager: a keymanager instance
        :type keymanager: keymanager.KeyManager

        :param soledad: a soledad instance
        :type soledad: Soledad

        """
        QtCore.QObject.__init__(self)

        leap_assert(keymanager, "Need a keymanager to initialize")
        leap_assert_type(soledad, Soledad)

        self._keymanager = keymanager
        self._soledad = soledad

        self._pkey = keymanager.get_all_keys_in_local_db(private=True).pop()
        self.chatlist = None
        self._loop = None

        self._create_soledad_indexes()

    def _create_soledad_indexes(self):
        """
        Create needed indexes on soledad.
        """
        self._soledad.create_index("chat-logs", "chat-with")

    def fetch(self, jid):
        """
        Fetch incoming mail, to be called periodically.

        Calls a deferred that will execute the fetch callback
        in a separate thread
        """
        self._chat_with = jid

        logger.debug('Fetching chat logs...')
        d = deferToThread(self._sync_soledad)
        d.addCallbacks(self._process_chatlist, self._sync_soledad_err)
        return d

    def get_chat_doc(self, chat_with):
        """
        Returns the chat document if exists or creates a empty one.

        :rtype: u1db document
        """
        # doc format
        chat = {
            'chat-with': '',
            'chats': []
        }
        # chat['chats'] = [{
        #     'from': 'user1@host.com',
        #     'msg': 'hola, como va?'
        # }]

        docs = self._soledad.get_from_index("chat-logs", chat_with)
        doc = None

        if len(docs) == 1:
            doc = docs[0]
            logger.debug('Using existing document for chat with: {0}'.format(
                chat_with))
        elif len(docs) == 0:
            chat['chat-with'] = chat_with
            doc = self._soledad.create_doc(chat)
            logger.debug('Creating new document for chat with: {0}'.format(
                chat_with))
        else:
            logger.error('Problem, unexpected number of chats.')

        logger.debug(doc)
        return doc

    def save_chat(self, message):
        chat_with = self._chat_with
        chat_from = message.get_jid()
        doc = self.get_chat_doc(chat_with)

        chat = {'from': chat_from, 'msg': message.get_message()}
        doc.content['chats'].append(chat)

        logger.debug('Updating document for chat with: {0}'.format(
            chat_with))

        doc = self._soledad.put_doc(doc)
        logger.debug(doc)
        # self._soledad.sync()

    def _sync_soledad(self):
        logger.debug('Syncing soledad...')
        soledad = self._soledad

        try:
            soledad.sync()
            # chatlist = self._soledad.get_from_index("chat-logs", "*")
            chatlist = soledad.get_from_index("chat-logs", self._chat_with)
            logger.debug("There are %s chats" % (len(chatlist), ))
            return chatlist
        except ssl.SSLError as exc:
            logger.warning('SSL Error while syncing soledad: %r' % (exc,))
        except Exception as exc:
            logger.warning('Error while syncing soledad: %r' % (exc,))

    def _sync_soledad_err(self, f):
        logger.err("Error syncing soledad: %s" % (f.value,))
        return f

    def _process_chatlist(self, chatlist):
        logger.debug('Processing chatlist')
        if not chatlist:
            logger.debug("No chats found")
            return
        for chat in chatlist:
            logger.debug("processing chat: %s" % chat)
            keys = chat.content.keys()
            logger.debug('Chat content: {0}'.format(chat.content))
            logger.debug('Chat with: {0}'.format(chat.content['chat-with']))
            for msg in chat.content['chats']:
                logger.debug('  {0} say: {1}'.format(msg['from'], msg['msg']))
            # self._soledad.delete_doc(chat)

        self.chatlist = chatlist
        self.chat_logs_ready.emit()
        return

        # ivan: imap code:
        if self.ENC_SCHEME_KEY in keys and self.ENC_JSON_KEY in keys:

            # XXX should check for _enc_scheme == "pubkey" || "none"
            # that is what incoming mail uses.
            encdata = chat.content[self.ENC_JSON_KEY]
            d = defer.Deferred(self._decrypt_msg(chat, encdata))
            d.addCallbacks(self._process_decrypted, log.msg)
        else:
            logger.debug('This does not look like a proper msg.')

    def encrypt_msg(self, from_address, to_address, data):
        """
        Encrypt a message.

        Fetch the recipient key and encrypt the content to the
        recipient. If a key is not found, then the behaviour depends on the
        configuration parameter ENCRYPTED_ONLY_KEY. If it is False, the message
        is sent unencrypted and a warning is logged. If it is True, the
        encryption fails with a KeyNotFound exception.

        @raise KeyNotFound: Raised when the recipient key was not found and
            the ENCRYPTED_ONLY_KEY configuration parameter is set to True.
        """
        logger.debug('encrypting msg')
        # signkey = self._keymanager.get_key(
        #     from_address, OpenPGPKey, private=True)
        signkey = self._pkey
        logger.debug("Will sign the message with %s." % signkey.fingerprint)
        encdata = data
        try:
            # try to get the recipient pubkey
            pubkey = self._keymanager.get_key(to_address, OpenPGPKey)
            logger.debug("Will encrypt the message to %s" % pubkey.fingerprint)
            encdata = self._keymanager.encrypt(data, pubkey, sign=signkey)
        except KeyNotFound:
            # at this point we _can_ send unencrypted mail, because if the
            # configuration said the opposite the address would have been
            # rejected in SMTPDelivery.validateTo().
            # self._sign_payload_rec(self._message, signkey)
            logger.debug('Will send unencrypted message to %s.' % to_address)

        return encdata

    def _decrypt_msg(self, encdata):
        logger.debug('decrypting msg')
        key = self._pkey
        decrdata = (self._keymanager.decrypt(
            encdata, key,
            # XXX get from public method instead
            passphrase=self._soledad._passphrase))

        return decrdata
