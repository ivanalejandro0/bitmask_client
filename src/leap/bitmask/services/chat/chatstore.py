import logging
import json
import ssl

from PySide import QtCore

from twisted.python import log
from twisted.internet import defer
from twisted.internet.threads import deferToThread

from leap.common.check import leap_assert, leap_assert_type
from leap.soledad import Soledad

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

    def _decrypt_msg(self, doc, encdata):
        logger.debug('decrypting msg')
        key = self._pkey
        decrdata = (self._keymanager.decrypt(
            encdata, key,
            # XXX get from public method instead
            passphrase=self._soledad._passphrase))

        # XXX TODO: defer this properly
        return self._process_decrypted(doc, decrdata)

    def _process_decrypted(self, doc, data):
        """
        Process a successfully decrypted message.

        :param doc: a SoledadDocument instance containing the incoming message
        :type doc: SoledadDocument

        :param data: the json-encoded, decrypted content of the incoming
                     message
        :type data: str

        :param inbox: a open SoledadMailbox instance where this message is
                      to be saved
        :type inbox: SoledadMailbox
        """
        logger.debug("processing incoming message!")
        msg = json.loads(data)
        if not isinstance(msg, dict):
            return False
        if not msg.get(self.INCOMING_KEY, False):
            return False
        # ok, this is an incoming message
        rawmsg = msg.get(self.CONTENT_KEY, None)
        if not rawmsg:
            return False
        logger.debug('got incoming message: %s' % (rawmsg,))

        try:
            pgp_beg = "-----BEGIN PGP MESSAGE-----"
            pgp_end = "-----END PGP MESSAGE-----"
            if pgp_beg in rawmsg:
                first = rawmsg.find(pgp_beg)
                last = rawmsg.rfind(pgp_end)
                pgp_message = rawmsg[first:first + last]

                decrdata = (self._keymanager.decrypt(
                    pgp_message, self._pkey,
                    # XXX get from public method instead
                    passphrase=self._soledad._passphrase))
                rawmsg = rawmsg.replace(pgp_message, decrdata)
            # add to inbox and delete from soledad
            self._inbox.addMessage(rawmsg, (self.RECENT_FLAG,))
            doc_id = doc.doc_id
            self._soledad.delete_doc(doc)
            logger.debug("deleted doc %s from incoming" % doc_id)
        except Exception as e:
            logger.error("Problem processing incoming mail: %r" % (e,))
