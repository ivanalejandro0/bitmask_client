from PySide import QtCore

from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish import domish

from utils import get_log_handler

logger = get_log_handler(__name__)


class ChatClient(QtCore.QObject):
    login_signal = QtCore.Signal()
    new_message_signal = QtCore.Signal(str, str)

    def __init__(self):
        QtCore.QObject.__init__(self)
        self._my_jid = ''
        self._the_xml_stream = None

    def login(self, username, password):
        from twisted.internet import reactor

        self._my_jid = jid.JID(username)

        factory = client.basicClientFactory(self._my_jid, password)
        factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failed)

        reactor.connectTCP('wtfismyip.com', 5222, factory)
        reactor.runReturn()

    def rawDataIn(self, buf):
        """
        Debug helper
        """
        log = "RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')
        logger.debug(log)

    def rawDataOut(self, buf):
        """
        Debug helper
        """
        log = "SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')
        logger.debug(log)

    def connected(self, xml_stream):
        logger.debug('Connected.')
        self._the_xml_stream = xml_stream

        # Log all traffic
        xml_stream.rawDataInFn = self.rawDataIn
        xml_stream.rawDataOutFn = self.rawDataOut

    def authenticated(self, xml_stream):
        logger.debug("Authenticated.")
        self.login_signal.emit()

        presence = domish.Element(('jabber:client', 'presence'))
        xml_stream.send(presence)

        xml_stream.addObserver('/message',  self.got_message)
        # xml_stream.addObserver('/presence', self.debug)
        # xml_stream.addObserver('/iq',       self.debug)

    def init_failed(self, failure):
        logger.debug("Initialization failed.")
        logger.debug(failure)

        self._the_xml_stream.sendFooter()

    def got_message(self, elem):
        logger.debug('Got message.')
        # before the remote user answer, the client sends more data
        # which is to inform tha the user is typing. aka 'activity'?

        msg = ''
        try:
            if len(elem.children) in (1, 2):
                msg = elem.children[0].children[0].encode('utf-8')

            if len(elem.children) == 3:
                msg = elem.children[1].children[0].encode('utf-8')

            if msg:
                sender = elem['from']
                self.new_message_signal.emit(sender, msg)
        except IndexError:
            # this try was added to avoid going deep in the parsing of elem
            pass

    def send_message(self, user_to, msg):
        sender = self._my_jid.full()
        to = jid.JID(user_to).full()

        message = domish.Element(('jabber:client', 'message'))
        message["to"] = to
        message["from"] = sender
        message["type"] = "chat"
        message.addElement("body", "jabber:client", msg)

        log = "send_message: %s, from: %s, to: %s" % (msg, sender, to)
        logger.debug(log)
        self._the_xml_stream.send(message)
