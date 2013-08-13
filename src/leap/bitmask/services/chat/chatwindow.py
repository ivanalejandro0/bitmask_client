import os
import sys
import signal

from PySide import QtCore, QtDeclarative, QtGui

from messages import Controller, MessageListModel
from messages import Message, MessageWrapper

from utils import get_log_handler

logger = get_log_handler(__name__)


def get_demo_messages():
    # Some example data
    jid_1 = "john@doe.com"
    jid_2 = "juan@perez.com"
    messages = [
        Message('Hello world!', jid_1),
        Message('Hello too', jid_2),
        Message('something original?', jid_1),
        Message('nope', jid_2),
        Message('123', jid_2),
        Message('testing...', jid_1),
    ]

    messages = [MessageWrapper(msg) for msg in messages]
    return messages


class ChatWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        view = QtDeclarative.QDeclarativeView()
        view.setResizeMode(QtDeclarative.QDeclarativeView.SizeRootObjectToView)

        messages_model = MessageListModel(get_demo_messages())
        self._controller = controller = Controller(messages_model)

        # Add context properties to use this objects from qml
        rc = view.rootContext()
        rc.setContextProperty('controller', controller)
        rc.setContextProperty('listModel', messages_model)

        full_path = os.path.realpath(__file__)
        folder = os.path.dirname(full_path)
        qml_file = os.path.join(folder, 'qml', 'Chat.qml')

        qml_qurl = QtCore.QUrl.fromLocalFile(qml_file)
        view.setSource(qml_qurl)

        self.setCentralWidget(view)

    def closeEvent(self, e):
        """
        Reimplementation of closeEvent to logout the chat.
        """
        # self._controller.logout()
        QtGui.QMainWindow.closeEvent(self, e)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    # Install the reactor (twisted <-> qt)
    import qt4reactor
    qt4reactor.install()

    window = ChatWindow()
    window.show()

    # Ensure that the application quits using CTRL-C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(app.exec_())
