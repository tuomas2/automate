# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of Automate.
#
# Automate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Automate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Automate.  If not, see <http://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------
#
# If you like Automate, please take a look at this page:
# http://evankelista.net/automate/

from __future__ import absolute_import
from __future__ import unicode_literals
from past.builtins import basestring
from copy import copy
import logging
import re
import keyword
import threading
from collections import Iterable
from functools import wraps

from traits.api import CSet, HasStrictTraits, Unicode, TraitType


class AbstractStatusObject(object):

    """
        Only reason for this abstract baseclass is that we need to avoid import loops
        between statusobject.py and various other modules.
    """


class SystemNotReady(Exception):
    pass


class ExitException(Exception):
    pass


class SystemBase(HasStrictTraits):
    pass


class Group(object):
    pass


class Object(object):

    """
        Class to refer explicitly objects by name
    """

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class LogicStr(Unicode):

    def validate(self, obj, name, value):
        v = value
        f = obj.system.eval_in_system_namespace(v)
        if f is None:
            self.error(obj, name, value)
        return value


class NameOrSensorActuatorBaseTrait(TraitType):

    def validate(self, obj, name, value):
        from .statusobject import StatusObject
        v = value
        if isinstance(v, StatusObject):
            return v
        if isinstance(v, basestring):
            return obj.system.name_to_system_object(v)
        self.error(obj, name, value)
        return value


def threaded(func, *args, **kwargs):
    """ uses thread_init as a decorator-style """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import traceback
            logging.getLogger('automate.common').error(
                "Exception occurred in thread: %s\n Traceback: \n %s", e, traceback.format_exc())
            return False

    return lambda: wrapper(*args, **kwargs)


def thread_start(func, *args, **kwargs):
    tfunc = threaded(func, *args, **kwargs)
    t = threading.Thread(target=tfunc, name='thread_start')
    t.start()
    return t


def is_valid_variable_name(name):
    return re.match("^[_A-Za-z][_a-zA-Z0-9]*$", name) and not keyword.iskeyword(name)


def has_baseclass(v, s):
    try:
        return issubclass(v, s)
    except TypeError:
        return False


class Lock(object):

    """Lock object (similar to threading.Lock) that can print some debug information"""
    context = None

    def __init__(self, name="Unnamed lock", silent=False):
        self.logger = logging.getLogger('automate.lock')
        self.name = name
        self.lock = threading.Lock()
        self.context_lock = threading.Lock()
        self.silent = silent

    def acquire(self, wait=0):
        return self.__enter__()

    def release(self):
        return self.__exit__(None, None, None)

    def __enter__(self):
        import traceback
        if self.lock.acquire(False):
            pass
        else:
            self.logger.debug("WAITING for lock %s", self.name)
            with self.context_lock:
                if not self.silent and self.context:
                    current_context = traceback.format_stack()
                    self.logger.debug("Current context:\n %s", "".join(current_context))
                    self.logger.debug("The context, when lock was acquired\n %s", "".join(self.context))
            self.lock.acquire()
            self.logger.debug("OK, gone through %s", self.name)

        with self.context_lock:
            self.context = traceback.format_stack()

    def __exit__(self, type, value, tb):
        with self.context_lock:
            self.context = None
        self.lock.release()


class _nomutex(object):

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

nomutex = _nomutex()


class CompareMixin(object):

    """Comparison and other operators that are common for Sensors,
       Actuators and callables.py operations

       """

    def __mul__(self, obj):
        from . import callables

        return callables.Product(self, obj)

    def __add__(self, obj):
        from . import callables

        return callables.Sum(self, obj)

    def __sub__(self, obj):
        from . import callables

        return callables.Sum(self, -obj)

    def __neg__(self):
        from . import callables

        return callables.Neg(self)

    def __lt__(self, obj):
        from . import callables

        return callables.Less(self, obj)

    def __gt__(self, obj):
        from . import callables
        return callables.More(self, obj)


class TagSet(CSet):

    def validate(self, object, name, value):
        if isinstance(value, basestring):
            return set((i.strip() for i in value.split(',')))
        return super(TagSet, self).validate(object, name, value)


def is_iterable(y):
    if isinstance(y, basestring):
        return False
    return isinstance(y, Iterable)


class DictObject(dict):

    def __getattr__(self, item):
        if item in self:
            return self[item]

    def __setattr__(self, key, value):
        self[key] = value

    def get_or_create(self, k, default):
        if k in self:
            return self[k]
        else:
            self[k] = default
            return default


def deep_iterate(l):
    if is_iterable(l):
        l_list = l
        if isinstance(l, dict):
            l_list = list(l.values())
        for i in l_list:
            if is_iterable(i):
                for j in deep_iterate(i): #TODO: could use yield from (python 3.3)
                    yield j
            else:
                yield i
    else:
        yield l


def get_modules_all(base_class, _locals):
    r_types = {}
    for k, v in list(copy(_locals).items()):
        if has_baseclass(v, base_class) and v is not base_class:
            r_types[k] = v

    return list(r_types.keys())
