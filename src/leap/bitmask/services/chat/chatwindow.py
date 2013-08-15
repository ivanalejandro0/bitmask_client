# -*- coding: utf-8 -*-
# chatwindow.py
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
Main window for the chat service.
"""
import os
import sys
import signal

from PySide import QtCore, QtDeclarative, QtGui

from messages import Controller, MessageListModel
from messages import Message, MessageWrapper

from utils import get_log_handler
from chatstore import ChatStore

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
    def __init__(self, window):
        QtGui.QMainWindow.__init__(self)

        view = QtDeclarative.QDeclarativeView()
        view.setResizeMode(QtDeclarative.QDeclarativeView.SizeRootObjectToView)

        # messages_model = MessageListModel(get_demo_messages())
        messages_model = MessageListModel()
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

        self._window = window
        window.soledad_ready.connect(self._create_chat_store)

    def closeEvent(self, e):
        """
        Reimplementation of closeEvent to logout the chat.
        """
        # self._controller.logout()
        QtGui.QMainWindow.closeEvent(self, e)

    def _create_chat_store(self):
        logger.debug('Soledad ready... creating ChatStore')
        keymanager = self._window._keymanager
        soledad = self._window._soledad

        chat_store = ChatStore(keymanager, soledad)
        self._controller.set_chat_store(chat_store)


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
