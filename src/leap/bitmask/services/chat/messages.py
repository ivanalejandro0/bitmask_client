from PySide import QtCore
from chatclient import ChatClient

from utils import get_log_handler

logger = get_log_handler(__name__)


class Message(object):
    """
    A basic implementation of a message.
    """
    def __init__(self, msg, jid):
        self._message = msg
        self._jid = jid

    def get_message(self):
        return self._message

    def get_jid(self):
        return self._jid

    def __str__(self):
        return '<Message jid: %s, message: %s>' % (self._jid, self._message)


class MessageWrapper(QtCore.QObject):
    """
    A wrapper for the object that we need to display in the list.
    """
    def __init__(self, message):
        QtCore.QObject.__init__(self)
        self._message = message

    def _text(self):
        msg = self._message.get_message()
        jid_ = self._message.get_jid()
        return '<b>%s says:</b> %s' % (jid_, msg)

    def __str__(self):
        return str(self._message)

    changed = QtCore.Signal()

    text = QtCore.Property(unicode, _text, notify=changed)


class MessageListModel(QtCore.QAbstractListModel):
    """
    The model for the ListView, it allows the list to access the data.
    """
    def __init__(self, demo_messages=None):
        QtCore.QAbstractListModel.__init__(self)
        self._messages = demo_messages
        if demo_messages is None:
            self._messages = []

        self.setRoleNames({0: 'messageItem'})

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._messages)

    def data(self, index, role):
        if index.isValid() and role == 0:
            return self._messages[index.row()]
        return None

    def addItem(self, message):
        # While we could use QAbstractItemModel::insertRows(), we'd have to
        # shoehorn around the API to get things done: we'd need to call
        # setData() etc.
        # The easier way, in this case, is to use our own method to do the
        # heavy lifting.
        count = len(self._messages)
        self.beginInsertRows(QtCore.QModelIndex(), count, count)
        self._messages.append(message)
        self.endInsertRows()


class Controller(QtCore.QObject):
    """
    A basic controller class that helps to interact between qml and python.
    """
    def __init__(self, model):
        QtCore.QObject.__init__(self)

        self._chat_client = ChatClient()
        self._chat_client.login_signal.connect(self.set_logged_in)
        self._chat_client.new_message_signal.connect(self.new_message)

        self._model = model
        self._logged_in = False
        self._user_from = ''
        self._user_to = ''

    @QtCore.Slot(QtCore.QObject)
    def itemSelected(self, wrapper):
        print 'User clicked on:', wrapper

    @QtCore.Slot(QtCore.QObject)
    def logged_in(self):
        return self._logged_in

    @QtCore.Slot(str)
    def set_user_to(self, user_to):
        self._user_to = user_to

    @QtCore.Slot(str, str, QtCore.QObject)
    def login(self, user, password, widget):
        self._logged_in = True
        self._user_from = user
        self._login_widget = widget

        self._chat_client.login(user, password)

    def _stop_reactor(self):
        """
        Stop the mainloop.
        This is useful if the chat app is used stand alone.
        """
        from twisted.internet import error, reactor
        logger.debug('stopping twisted reactor')
        try:
            reactor.stop()
        except error.ReactorNotRunning:
            logger.debug('reactor not running')

    def set_logged_in(self):
        """
        SLOT:
            this function gets called when the chat_client emits
            the login_signal.
        """
        self._login_widget.setProperty('loggedIn', 'true')

    @QtCore.Slot(QtCore.QObject)
    def send_message(self, message):
        text = message.property('text')

        self._chat_client.send_message(self._user_to, text)
        self.new_message(self._user_from, text)

        message.setProperty('text', '')

    def new_message(self, sender, message):
        logger.debug('new message')
        msg = MessageWrapper(Message(message, sender))
        self._model.addItem(msg)
