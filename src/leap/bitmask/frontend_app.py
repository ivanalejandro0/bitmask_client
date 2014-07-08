# -*- coding: utf-8 -*-
# frontend_app.py
# Copyright (C) 2013, 2014 LEAP
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
Start point for the Frontend.
"""
import multiprocessing
import signal
import sys
import os

from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask.config import flags
from leap.bitmask.gui import locale_rc  # noqa - silence pylint
from leap.bitmask.gui.mainwindow import MainWindow
from leap.bitmask.util import dict_to_flags

import logging
logger = logging.getLogger(__name__)


def signal_handler(window, signum, frame):
    """
    Signal handler that quits the running app cleanly.

    :param window: a window with a `quit` callable
    :type window: MainWindow
    :param signum: number of the signal received (e.g. SIGINT -> 2)
    :type signum: int
    :param frame: current stack frame
    :type frame: frame or None
    """
    pname = multiprocessing.current_process().name
    logger.debug("{0}: SIGNAL #{1} catched.".format(pname, signum))
    window.quit()


def run_frontend(options, flags_dict):
    """
    Run the GUI for the application.

    :param options: a dict of options parsed from the command line.
    :type options: dict
    :param flags_dict: a dict containing the flag values set on app start.
    :type flags_dict: dict
    """
    dict_to_flags(flags_dict)

    start_hidden = options["start_hidden"]

    # We force the style if on KDE so that it doesn't load all the kde
    # libs, which causes a compatibility issue in some systems.
    # For more info, see issue #3194
    if flags.STANDALONE and os.environ.get("KDE_SESSION_UID") is not None:
        sys.argv.append("-style")
        sys.argv.append("Cleanlooks")

    qApp = QtGui.QApplication(sys.argv)

    # To test:
    # $ LANG=es ./app.py
    locale = QtCore.QLocale.system().name()
    qtTranslator = QtCore.QTranslator()
    if qtTranslator.load("qt_%s" % locale, ":/translations"):
        qApp.installTranslator(qtTranslator)
    appTranslator = QtCore.QTranslator()
    if appTranslator.load("%s.qm" % locale[:2], ":/translations"):
        qApp.installTranslator(appTranslator)

    # Needed for initializing qsettings it will write
    # .config/leap/leap.conf top level app settings in a platform
    # independent way
    qApp.setOrganizationName("leap")
    qApp.setApplicationName("leap")
    qApp.setOrganizationDomain("leap.se")

    # HACK:
    # We need to do some 'python work' once in a while, otherwise, no python
    # code will be called and the Qt event loop will prevent the signal
    # handlers for SIGINT/SIGTERM to be called.
    # see: http://stackoverflow.com/a/4939113/687989
    timer = QtCore.QTimer()
    timer.start(500)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    window = MainWindow(start_hidden=start_hidden)

    sigterm_handler = partial(signal_handler, window)
    # ignore SIGINT since app.py takes care of signaling SIGTERM to us.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, sigterm_handler)

    sys.exit(qApp.exec_())


if __name__ == '__main__':
    run_frontend()
