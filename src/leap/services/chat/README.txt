First approarch to a XMPP chat application using QML as UI.
===========================================================

There are pre-loaded data in the widgets to speed up the testing.

The app logs in with the default values:
user: 1234test1234@wtfismyip.com
pass: asdfasdf

You can use a client like pidgin to chat with yourself in order to test 
the app.
Another test account to test:
user: 123test123@wtfismyip.com
pass: asdfasdf

NOTE: this account has been already accepted in the other user's roaster
list, initially tested with pidgin.

Requirements
------------
To use the application you need to install: Twisted and PySide


Usage
-----

Option 1)
Just run the leap client, the chat window will show up automatically.
run: `python src/leap/app.py -d --danger`

Option 2)
Run in the terminal: `python chatwindow.py`

The application has 3 'screens': login, chat-with-who, chat-itself

The login screen has 2 text widgets to enter username and password, you accept
and move forward pressing ENTER.

The chat-with-who screen has only one widget in which you need to enter the JID
of the user you want to chat to.

The chat-itself has a list of messages (it starts with some dummy messages loaded)
and a input box where you can type a message to send.
The list of messages won't automatically scroll when a new message is received/send,
you need to do it manually by now.


To quit the application you have to press CTRL+C in the terminal. The 'x' button in
the window won't finish the twisted instance.
