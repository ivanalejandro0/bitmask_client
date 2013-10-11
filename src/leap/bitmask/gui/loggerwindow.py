# -*- coding: utf-8 -*-
# loggerwindow.py
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
History log window
"""
import logging

from PySide import QtGui

from ui_loggerwindow import Ui_LoggerWindow

from leap.bitmask.util.leap_log_handler import LeapLogHandler
from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)


class LoggerWindow(QtGui.QDialog):
    """
    Window that displays a history of the logged messages in the app.
    """
    MAX_LOGS = 200

    def __init__(self, handler):
        """
        Initialize the widget with the custom handler.

        :param handler: Custom handler that supports history and signal.
        :type handler: LeapLogHandler.
        """
        QtGui.QDialog.__init__(self)
        leap_assert(handler, "We need a handler for the logger window")
        leap_assert_type(handler, LeapLogHandler)

        # Load UI
        self.ui = Ui_LoggerWindow()
        self.ui.setupUi(self)

        # Make connections
        self.ui.btnSave.clicked.connect(self._save_log_to_file)
        self.ui.btnDebug.toggled.connect(self._filter_level),
        self.ui.btnInfo.toggled.connect(self._filter_level),
        self.ui.btnWarning.toggled.connect(self._filter_level),
        self.ui.btnError.toggled.connect(self._filter_level),
        self.ui.btnCritical.toggled.connect(self._filter_level)
        self.ui.btnSearch.clicked.connect(self._filter_message)
        self.ui.btnFirstPage.clicked.connect(self._first_page)
        self.ui.btnPreviousPage.clicked.connect(self._previous_page)
        self.ui.btnNextPage.clicked.connect(self._next_page)
        self.ui.btnLastPage.clicked.connect(self._last_page)

        # Initialize filters
        self._message_filter = ""
        self._levels_filter = None

        # Load logging history and connect logger with the widget
        self._logging_handler = handler
        self._history_offset = 0

        self._connect_to_handler()
        self._to_last_page()
        self._load_history()

    def _connect_to_handler(self):
        """
        This method connects the loggerwindow with the handler through a
        signal communicate the logger events.
        """
        self._logging_handler.new_log.connect(self._add_new_log)

    def _add_new_log(self, log):
        """
        SLOT
        TRIGGER:
            self._logging_handler.new_log

        Adds a new log line when is emitted by the handler.

        :param log: a log record to be inserted in the widget
        :type log: a dict with LEVEL_KEY and MESSAGE_KEY.
            the level number of the message,
            the message contains the formatted message for the log.
        """
        is_last_page = self.ui.btnNextPage.isEnabled()
        if not is_last_page:
            self._to_last_page()

        self._load_history()

        if not is_last_page:
            self._add_log_line(log)

    def _format_log_line(self, message, level):
        """
        Formats the log line to be displayed as html in the logs window.

        :param message: the message to format
        :type message: str
        :param level: the level of the message to format
        :type level: int
        """
        html_style = {
            logging.DEBUG: "background: #CDFFFF;",
            logging.INFO: "background: white;",
            logging.WARNING: "background: #FFFF66;",
            logging.ERROR: "background: red; color: white;",
            logging.CRITICAL: "background: red; color: white; font: bold;"
        }
        open_tag = "<tr style='" + html_style[level] + "'>"
        open_tag += "<td width='100%' style='padding: 5px;'>"
        close_tag = "</td></tr>"
        message = open_tag + message + close_tag

        return message

    def _add_log_line(self, log):
        """
        Adds a line to the history, only if it's in the desired levels to show.

        :param log: a log record to be inserted in the widget
        :type log: a dict with LEVEL_KEY and MESSAGE_KEY.
            the level number of the message,
            the message contains the formatted message for the log.
        """
        level = log[LeapLogHandler.LEVEL_KEY]
        message = log[LeapLogHandler.MESSAGE_KEY]

        message = self._format_log_line(message, level)
        self.ui.txtLogHistory.append(message)

    def _load_history(self):
        """
        Load the previous logged messages in the widget.
        They are stored in the custom handler.
        """
        self.ui.txtLogHistory.clear()

        history = self._logging_handler.log_history
        history.set_limit(self.MAX_LOGS, self._history_offset)

        for line in history.get_logs():
            self._add_log_line(line)

        count = history.count_query_result()
        pages = count / self.MAX_LOGS + 1
        status = "Showing {0} of {1} logs. Page {2} of {3}.".format(
            count, history.count_items(),
            self._history_offset + 1, pages)
        self.ui.lblLogsStatus.setText(status)

        # Enable or disable the Previous button
        prev_enabled = self._history_offset > 0
        self.ui.btnPreviousPage.setEnabled(prev_enabled)
        self.ui.btnFirstPage.setEnabled(prev_enabled)

        # Enable or disable the Next button
        next_enabled = pages > 1 and self._history_offset + 1 < pages
        self.ui.btnNextPage.setEnabled(next_enabled)
        self.ui.btnLastPage.setEnabled(next_enabled)

    def _filter_level(self):
        """
        Sets the level filter for the queries.
        """
        levels = {
            logging.DEBUG: self.ui.btnDebug.isChecked(),
            logging.INFO: self.ui.btnInfo.isChecked(),
            logging.WARNING: self.ui.btnWarning.isChecked(),
            logging.ERROR: self.ui.btnError.isChecked(),
            logging.CRITICAL: self.ui.btnCritical.isChecked()
        }
        levels = [key for (key, value) in levels.items() if levels[key]]
        self._levels_filter = levels

        history = self._logging_handler.log_history
        history.set_filter(message=self._message_filter, levels=levels)

        self._to_last_page()
        self._load_history()

    def _filter_message(self):
        """
        Sets the message filter for the queries.
        """
        self._message_filter = self.ui.leFilterBy.text()

        history = self._logging_handler.log_history
        history.set_filter(message=self._message_filter,
                           levels=self._levels_filter)

        self._to_last_page()
        self._load_history()

    def _previous_page(self):
        """
        SLOT
        TRIGGER:
            self.ui.btnPreviousPage.clicked

        Moves the offset to the previous page of the logs,
        and reloads the history.
        """
        self._history_offset -= 1
        self._load_history()

    def _next_page(self):
        """
        SLOT
        TRIGGER:
            self.ui.btnNextPage.clicked

        Moves the offset to the next page of the logs,
        and reloads the history.
        """
        self._history_offset += 1
        self._load_history()

    def _first_page(self):
        """
        SLOT
        TRIGGER:
            self.ui.btnFirstPage.clicked

        Moves the offset to the first page of the logs,
        and reloads the history.
        """
        self._history_offset = 0
        self._load_history()

    def _last_page(self):
        """
        SLOT
        TRIGGER:
            self.ui.btnLastPage.clicked

        Moves the offset to the last page of the logs,
        and reloads the history.
        """
        self._to_last_page()
        self._load_history()

    def _to_last_page(self):
        """
        Moves the offset to the last page of the logs.
        """
        history = self._logging_handler.log_history
        count = history.count_query_result()
        last_page = count / self.MAX_LOGS
        self._history_offset = last_page

    def _save_log_to_file(self):
        """
        Lets the user save the current log to a file
        """
        fileName, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save As"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                with open(fileName, 'w') as output:
                    history = self.ui.txtLogHistory.toPlainText()
                    # Chop some \n.
                    # html->plain adds several \n because the html is made
                    # using table cells.
                    history = history.replace('\n\n\n', '\n')

                    output.write(history)
                logger.debug('Log saved in %s' % (fileName, ))
            except IOError, e:
                logger.error("Error saving log file: %r" % (e, ))
        else:
            logger.debug('Log not saved!')
