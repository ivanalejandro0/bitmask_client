# -*- coding: utf-8 -*-
# messages.py
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
Message abstraction classes, models and controller.
"""
import logging

from PySide import QtCore
from chatclient import ChatClient

logger = logging.getLogger(__name__)


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

        self._chat_store = None

        # list to store messages that can't be saved until soledad is available
        self._not_saved_msgs = []

    @QtCore.Slot(QtCore.QObject)
    def itemSelected(self, wrapper):
        print 'User clicked on:', wrapper

    @QtCore.Slot(QtCore.QObject)
    def logged_in(self):
        return self._logged_in

    @QtCore.Slot(str, str)
    def set_user_to(self, user_to, bitmask_jid):
        logger.debug("Starting communcation with: {0}, {1}".format(
            user_to, bitmask_jid))
        self._user_to = user_to
        self._bitmask_jid = bitmask_jid

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
        logger.debug('Send message: {0}'.format(message))
        text = message.property('text')

        if self._chat_store is not None:
            et = self._chat_store.encrypt_msg(
                self._user_from, self._bitmask_jid, text)
            logger.debug('Encrypted msg: {0}'.format(et))
            dt = self._chat_store.decrypt_msg(et)
            logger.debug('Decrypted msg: {0}'.format(dt))

        # self._chat_client.send_message(self._user_to, text)
        self._chat_client.send_message(self._user_to, et)
        self.new_message(self._user_from, text)

        message.setProperty('text', '')

    def new_message(self, sender, message, store=True):
        logger.debug('new message')

        if self._chat_store is not None:
            message = self._chat_store._decrypt_msg(message)

        msg = Message(message, sender)
        msgw = MessageWrapper(msg)
        self._model.addItem(msgw)

        if not store:
            return

        if self._chat_store is None:
            self._not_saved_msgs.append(msg)
        # else:
        #     self._chat_store.save_chat(msg)

    def _load_history(self):
        chatlist = self._chat_store.chatlist
        for chat in chatlist:
            logger.debug("processing chat: %s" % chat)
            logger.debug('Chat content: {0}'.format(chat.content))
            logger.debug('Chat with: {0}'.format(chat.content['chat-with']))
            for msg in chat.content['chats']:
                logger.debug('  {0} say: {1}'.format(msg['from'], msg['msg']))
                self.new_message(msg['from'], msg['msg'], store=False)

            return

    def set_chat_store(self, chat_store):
        self._chat_store = chat_store
        self._chat_store.fetch(self._user_to)
        self._chat_store.chat_logs_ready.connect(self._load_history)

        # save pending messages into store
        for msg in self._not_saved_msgs:
            chat_store.save_chat(msg)
