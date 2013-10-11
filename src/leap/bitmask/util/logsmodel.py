# -*- coding: utf-8 -*-
# logsmodel.py
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


class LogsModel(object):
    """
    Class to model the log history as a db.
    """
    LOG_MESSAGE_KEY = 'message'
    LOG_LEVEL_KEY = 'levelno'

    def __init__(self):
        self._history = []
        self._query_filter = {'msg': "", 'levels': None}
        self._query_limit = {'limit': 0, 'offset': 0}

    def set_filter(self, message="", levels=None):
        """
        Specifies the filter to use in the next sql query.

        :param message: the filter to use in the 'message' column.
        :type message: str
        :param levels: the levels that we want to display.
        :type levels: list
        """
        self._query_filter = {'msg': message.upper(), 'levels': levels}

    def set_limit(self, items_limit=None, offset=None):
        """
        Specifies the limits to use in the next sql query.

        :param items_limit: the ammount of items to limit the query.
        :type items_limit: int
        :param offset: the offset or 'page' to return in the query.
        :type offset: int
        """
        self._query_limit = {'limit': items_limit, 'offset': offset}

    def count_query_result(self):
        """
        Returns the count for the current configuration of the query.

        :rtype: int
        """
        return len(self._history)

    def get_logs(self):
        """
        Returns a generator for the logs of the db.

        :rtype: dict {'message': str, 'levelno': int}
        """
        limit = self._query_limit['limit']
        offset = self._query_limit['offset']
        history = self._history[limit*offset:limit*(offset+1)]
        for item in history:
            msg = item[self.LOG_MESSAGE_KEY].upper()
            msg_filter = self._query_filter['msg']
            lvl = item[self.LOG_LEVEL_KEY]
            lvl_filter = self._query_filter['levels']

            log = item
            try:
                if msg_filter and msg_filter not in msg:
                    log = None

                if lvl_filter is not None and lvl not in lvl_filter:
                    log = None

                if log is not None:
                    yield log
            except ValueError:
                pass

    def count_items(self):
        """
        Returns the count of items in db.
        """
        return len(self._history)

    def save_item(self, log):
        """
        Inserts a new log in the db.

        :param log: a log dict with a message and a level
        :type log: dict
        """
        self._history.append(log)
