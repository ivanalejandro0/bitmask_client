# -*- coding: utf-8 -*-
# __init__.py
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
Some small and handy functions.
"""
import datetime
import itertools
import os
import shutil

from leap.bitmask.config import flags
from leap.common.config import get_path_prefix as common_get_path_prefix

# functional goodies for a healthier life:
# We'll give your money back if it does not alleviate the eye strain, at least.


def first(things):
    """
    Return the head of a collection.

    :param things: a sequence to extract the head from.
    :type things: sequence
    :return: object, or None
    """
    try:
        return things[0]
    except (IndexError, TypeError):
        return None


def flatten(things):
    """
    Return a generator iterating through a flattened sequence.

    :param things: a nested sequence, eg, a list of lists.
    :type things: sequence
    :rtype: generator
    """
    return itertools.chain(*things)


# leap repetitive chores

def get_path_prefix():
    """
    Return the bitmask prefix folder used as a base path for data storage.

    :rtype: str
    """
    return common_get_path_prefix(flags.STANDALONE)


def get_bitmask_config_path():
    """
    Return the bitmask configuration folder used to store all the application
    data.

    :rtype: str
    """
    return os.path.join(common_get_path_prefix(flags.STANDALONE), 'bitmask')


def _move_config_leap_to_bitmask():
    """
    Migration helper to move the old config folder path to the new path name.
    ~/.config/leap/ -> ~/.config/bitmask/

    :return: True if succeeded, False if not neccessary.
    :rtype: Bool

    May rise IOError if the new path exists.
    """
    OLD_CONFIG_PATH = os.path.join(get_path_prefix(), 'leap')
    NEW_CONFIG_PATH = os.path.join(get_path_prefix(), 'bitmask')

    if not os.path.exists(OLD_CONFIG_PATH):
        return False

    if os.path.exists(NEW_CONFIG_PATH):
        msg = ("Migration script failed: {0} -> {1}\n"
               "Can't migrate config folder since {1} exists.\n"
               "You need to choose whether you want to keep configs on {0} or"
               "{1} in order to fix this conflict.")
        msg = msg.format(OLD_CONFIG_PATH, NEW_CONFIG_PATH)
        raise IOError(msg)

    shutil.move(OLD_CONFIG_PATH, NEW_CONFIG_PATH)
    return True


def get_modification_ts(path):
    """
    Gets modification time of a file.

    :param path: the path to get ts from
    :type path: str
    :returns: modification time
    :rtype: datetime object
    """
    ts = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(ts)


def update_modification_ts(path):
    """
    Sets modification time of a file to current time.

    :param path: the path to set ts to.
    :type path: str
    :returns: modification time
    :rtype: datetime object
    """
    os.utime(path, None)
    return get_modification_ts(path)


def is_file(path):
    """
    Returns True if the path exists and is a file.
    """
    return os.path.isfile(path)


def is_empty_file(path):
    """
    Returns True if the file at path is empty.
    """
    return os.stat(path).st_size is 0


def make_address(user, provider):
    """
    Return a full identifier for an user, as a email-like
    identifier.

    :param user: the username
    :type user: basestring
    :param provider: the provider domain
    :type provider: basestring
    """
    return "%s@%s" % (user, provider)


def force_eval(items):
    """
    Return a sequence that evaluates any callable in the sequence,
    instantiating it beforehand if the item is a class, and
    leaves the non-callable items without change.
    """
    def do_eval(thing):
        if isinstance(thing, type):
            return thing()()
        if callable(thing):
            return thing()
        return thing

    if isinstance(items, (list, tuple)):
        return map(do_eval, items)
    else:
        return do_eval(items)


def dict_to_flags(values):
    """
    Set the flags values given in the values dict.
    If a value isn't provided then use the already existing one.

    :param values: the values to set.
    :type values: dict.
    """
    for k, v in values.items():
        setattr(flags, k, v)


def flags_to_dict():
    """
    Get the flags values in a dict.

    :return: the values of flags into a dict.
    :rtype: dict.
    """
    items = [i for i in dir(flags) if i[0] != '_']
    values = dict((i, getattr(flags, i)) for i in items)

    return values
