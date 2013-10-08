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

import atexit
import sqlite3 as dbapi


class LogsModel(object):
    """
    Class to model the log history as a db.
    """
    TABLE_NAME = 'logs'
    LOG_MESSAGE_KEY = 'message'
    LOG_LEVEL_KEY = 'levelno'

    def __init__(self, dbname=':memory:', init=False):
        """
        Constructor for the model.

        :param dbname: the name for the database, or ':memory:' to use
                       in-memory database.
        :type dbname: str
        :param init: True if we need to initialize the database,
                     False otherwise.
        :type init: bool
        """
        self._database = dbapi.connect(dbname, check_same_thread=False)
        self._cursor = self._database.cursor()
        atexit.register(self._close_db)

        if dbname == ':memory:' or init:
            self._init_db()

        self._query_filter = ""
        self._query_limit = ""

    def _close_db(self):
        """
        Closes the cursor and database at exit.
        """
        self._cursor.close()
        self._database.close()

    def _init_db(self):
        """
        Database bootstrapper, we use this method in case that the needed table
        does not exist.
        """
        query = "CREATE TABLE {table} (message TEXT, level TEXT)"
        query = query.format(table=self.TABLE_NAME)

        self._cursor.execute(query)
        self._database.commit()

    def set_filter(self, message="", levels=None):
        """
        Specifies the filter to use in the next sql query.

        :param message: the filter to use in the 'message' column.
        :type message: str
        :param levels: the levels that we want to display.
        :type levels: list
        """
        self._query_filter = ""
        where_and = ' WHERE'

        if message:
            self._query_filter = " WHERE message LIKE '%{0}%'".format(message)
            where_and = ' AND'

        if levels is not None:
            levels = ", ".join(["'{0}'".format(l) for l in levels])
            self._query_filter += where_and + " level IN ({0})".format(levels)

    def set_limit(self, items_limit=None, offset=None):
        """
        Specifies the limits to use in the next sql query.

        :param items_limit: the ammount of items to limit the query.
        :type items_limit: int
        :param offset: the offset or 'page' to return in the query.
        :type offset: int
        """
        self._query_limit = ''

        if items_limit is not None:
            self._query_limit = " LIMIT " + str(items_limit)
            if offset is not None:
                self._query_limit = (self._query_limit + ' OFFSET ' +
                                     str(offset * items_limit))

    def count_query_result(self):
        """
        Returns the count for the current configuration of the query.

        :rtype: int
        """
        query = "SELECT COUNT(*) FROM {table}{where}".format(
            table=self.TABLE_NAME,
            where=self._query_filter)
        self._cursor.execute(query)

        return self._cursor.fetchone()[0]

    def get_logs(self):
        """
        Returns a generator for the logs of the db.

        :rtype: dict {'message': str, 'levelno': int}
        """
        self.count_query_result()

        query = "SELECT * FROM {table}{where}{limit}".format(
            table=self.TABLE_NAME,
            where=self._query_filter,
            limit=self._query_limit)

        self._cursor.execute(query)

        for item in self._cursor:
            try:
                log = {
                    self.LOG_MESSAGE_KEY: item[0],
                    self.LOG_LEVEL_KEY: int(item[1])
                }
                yield log
            except ValueError:
                pass

    def count_items(self):
        """
        Returns the count of items in db.
        """
        query = 'SELECT COUNT(*) FROM {0}'.format(self.TABLE_NAME)
        self._cursor.execute(query)
        return self._cursor.fetchone()[0]

    def save_item(self, log):
        """
        Inserts a new log in the db.

        :param log: a log dict with a message and a level
        :type log: dict
        """
        # Use a local cursor to avoid threads problems.
        cursor = self._database.cursor()
        try:
            query = "INSERT INTO {0} VALUES (?, ?)".format(self.TABLE_NAME)
            arguments = (log[self.LOG_MESSAGE_KEY], log[self.LOG_LEVEL_KEY])
            cursor.execute(query, arguments)
            self._database.commit()
        except dbapi.IntegrityError:
            print "Integrity Error: repeated entry '{0}'.".format(
                log[self.LOG_MESSAGE_KEY])
