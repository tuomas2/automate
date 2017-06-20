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

from __future__ import unicode_literals
from builtins import bytes

import datetime

from future import standard_library

standard_library.install_aliases()

from http.client import HTTPException

import re
import threading
import xmlrpc.client
import socket
import subprocess

from traits.api import (CList, Any, Property, Set, Bool, Event, CBool, on_trait_change, cached_property)

from automate.callable import AbstractCallable
from automate.common import deep_iterate, get_modules_all
from automate.statusobject import StatusObject
from automate.common import (threaded, thread_start, is_iterable)


class Empty(AbstractCallable):

    """
        Do nothing but return None. Default action in Programs.

        Usage::

            Empty()
    """
    test = Bool(False)

    def call(self, caller, **kwargs):
        return None


class AbstractAction(AbstractCallable):

    """
        Abstract base class for actions (i.e. callables that do something but
        do not necessarily return anything.
    """
    status = Bool(True)


class Attrib(AbstractAction):

    """
        Give specified attribute of a object.

        :param no_eval bool: if True, evaluation of object is skipped -- use this to access attributes of SystemObjects

        Usage & example::

            Attrib(obj, 'attributename')
            Attrib(sensor_name, 'status', no_eval=True)


    """

    @property
    def method(self):
        return self._args[1]

    def call(self, caller, **kwargs):
        no_eval = self._kwargs.get('no_eval', False)
        if not caller:
            return
        if no_eval:
            obj = self.obj
        else:
            obj = self.call_eval(self.obj, caller, **kwargs)
        attr = self.call_eval(self.method, caller, **kwargs)
        return getattr(obj, attr, None)


class Method(AbstractAction):

    """
        Call method in an object with specified args

        Usage::

            Method(obj, 'methodname')
    """

    @property
    def method(self):
        return self._args[1]

    @property
    def args(self):
        try:
            return self._args[2:]
        except IndexError:
            return ()

    def call(self, caller, **kwargs):
        if not caller:
            return
        kwargs = self._kwargs.copy()
        if not kwargs.pop('no_caller', False):
            arglist = [caller] + list(self.args)
        else:
            arglist = self.args
        return getattr(self.call_eval(self.obj, caller, **kwargs), self.call_eval(self.method, caller, **kwargs))(*arglist, **kwargs)


class Func(AbstractAction):

    """
        Call function with given arguments.

        Usage & example::

            Func(function, *args, **kwargs)
            Func(time.sleep, 2)

        :param bool add_caller: if True, then caller program is passed as first argument.
    """

    @property
    def args(self):
        return tuple(self._args[1:])

    def call(self, caller, **kwargs):
        if not caller:
            return
        _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
        return_value = _kwargs.pop('return_value', True)
        args = [self.call_eval(i, caller, return_value=return_value, **kwargs) for i in self.args]
        if _kwargs.pop('add_caller', False):
            arglist = [caller] + list(args)
        else:
            arglist = args
        self.logger.debug("Func %s %s %s", self.obj, arglist, _kwargs)
        try:
            return self.call_eval(self.obj, caller, **kwargs)(*arglist, **_kwargs)
        except Exception as e:
            self.logger.error('Exception occurred in %s: %s', self, e)


class OnlyTriggers(AbstractCallable):

    """
    Baseclass for actions that do not have any targets (i.e. almost all actions).
    """

    def _give_targets(self):
        return None


class Log(OnlyTriggers):

    """
        Print callable argument outputs / other arguments to the log.

        Usage::

            Log(object1, object2, 'string1'...)

        :param str log_level: Log level (i.e. logging function name) (default 'info')
    """

    default_log_level = 'info'

    def call(self, caller, **kwargs):
        log_level = self._kwargs.get('log_level', self.default_log_level)
        l = []
        for o in self.objects:
            l.append(self.call_eval(o, caller, **kwargs))
        getattr(self.logger, log_level)(*l)
        return True


class Debug(Log):

    """
        Same as :class:`.Log` but with debug logging level.
    """
    default_log_level = 'debug'


class ToStr(OnlyTriggers):

    """
        Return string representation of given arguments evaluated.
        Usage::

            ToStr('formatstring {} {}', callable1, statusobject1)

        :param bool no_sub: if True, removes format string from argument list. Then usage is simply:

        .. code-block:: python

            ToStr(callable1, statusobject1, no_sub=True)
    """

    def call(self, caller, **kwargs):
        _kwargs = self._kwargs.copy()
        no_sub = _kwargs.pop('no_sub', False)
        if no_sub:
            rv = ' '.join([str(self.call_eval(i, caller, **kwargs)) for i in self.objects])
        else:
            rv = str(self.call_eval(self.obj, caller, **kwargs)).format(
                *[self.call_eval(i, caller, **kwargs) for i in self.objects[1:]], **_kwargs)
        return rv


class Eval(AbstractAction):

    """Execute python command given as a string with eval (or exec).

    Usage::

        Eval("print time.{param}()", pre_exec="import time", param="time")

    First argument: python command to be evaluated. If it can be evaluated by
    eval() then return value is the evaluated value. Otherwise, exec() is used and True
    is returned.

    :param str pre_exec: pre-execution string. For example necessary import commands.
    :param dict namespace: Namespace. Defaults to locals() in :mod:`.builtin_callables`.

    Optionally, other keyword arguments can be given, and they are replaced in the first argument
    by format().

    See also (and prefer using): :class:`.Func`
    """

    def call(self, caller, **kwargs):
        if not caller:
            return
        _kwargs = self._kwargs.copy()
        namespace = _kwargs.pop('namespace', locals())
        pre_exec = _kwargs.pop('pre_exec', '')

        if pre_exec:
            exec(pre_exec.format(**self._kwargs), namespace)
        try:
            return eval(self.obj.format(**self._kwargs), namespace)
        except SyntaxError:
            exec(self.obj.format(**self._kwargs), namespace)
            return True


class Exec(Eval):

    """Synonym to :class:`.Eval`"""


class GetService(AbstractAction):
    """
    Get service by name and number.

    Usage::

        GetService(name)
        GetService(name, number)

    Usage examples::

        GetService('WebService')
        GetService('WebService', 1)

    """
    def call(self, caller, **kwargs):
        name = self._args[0]
        num = self._args[1] if len(self._args) > 1 else 0
        return self.system.services_by_name[name][num]


class ReloadService(AbstractAction):
    """
    Reload given service.

    Usage::

        ReloadService(name, number)
        ReloadService(name)

    Usage examples::

        ReloadService('WebService', 0)
        ReloadService('ArduinoService')

    """
    def call(self, caller, **kwargs):
        name = self._args[0]
        num = self._args[1] if len(self._args) > 1 else 0
        return self.system.services_by_name[name][num].reload()


class Shell(AbstractAction):

    """
        Execute shell command and return string value

        :param bool no_wait: if True, execute shell command in new thread and return pid
        :param bool output: if True, execute will return the output written to stdout by shell command. By default,
                            execution status (integer) is returned.
        :param str input: if given, input is passed to stdin of the given shell command.

        Usage examples::

            Shell('/bin/echo test', output=True) # returns 'test'
            Shell('mplayer something.mp3', no_wait=True) # returns PID of mplayer
                                                         # process that keeps running
            Shell('/bin/cat', input='test', output=True) # returns 'test'.
    """

    def call(self, caller, **kwargs):
        cmd = self.call_eval(self.obj, caller, **kwargs)
        input = self._kwargs.get('input', None)
        if input:
            input = bytes(self.call_eval(input, caller, **kwargs), 'utf-8')
        if not caller:
            return
        try:
            process = subprocess.Popen(
                cmd, executable='bash', shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            self.logger.debug('Shell: cmd "%s", pid %s', cmd, process.pid)
            if self._kwargs.get('no_wait', False):
                thread_start(lambda: process.communicate(input))
                return process.pid
            else:
                out, err = process.communicate(input)
                retcode = process.poll()
                if self._kwargs.get('output', False):
                    return out.decode('utf-8')
                else:
                    return retcode
        except Exception as e:
            self.system.logger.error('Error %s in %s, cmd: %s', e, self, cmd)
        return -1


class SetStatus(AbstractAction):

    """
        Set sensor or actuator value

        Usage::

            SetStatus(target, source)
            # sets status of target to the status of source.
            SetStatus(target, source, Force=True)
            # sets status to hardware level even if it is not changed
            SetStatus([actuator1, actuator2], [sensor1, sensor2])
            # sets status of actuator 1 to status of sensor1 and
            # status of actuator2 to status of sensor2.
    """

    def call(self, caller=None, trigger=None, **kwargs):
        if not caller:
            return
        force = self._kwargs.get('force', False)
        values = self.call_eval(self.value, caller, **kwargs)
        objs = self.name_to_system_object(self.obj)
        if isinstance(objs, AbstractCallable):
            objs = self.call_eval(objs, caller, return_value=False, **kwargs)
        if not is_iterable(objs):
            objs = [objs]
        objs = list(objs)
        if not is_iterable(values):
            values = [values] * len(objs)
        values = list(values)
        assert len(objs) == len(values), ('SetStatus: length of targets should be equal to '
                                          'length of sources: %s != %s' % (len(objs), len(values)))

        self.system.logger.debug('SetStatus: objs %s, rv: %s', objs, values)
        for idx, obj in enumerate(objs):
            value = self.call_eval(values[idx], caller, **kwargs)
            obj = self.call_eval(obj, caller, return_value=False, trigger=trigger, **kwargs)
            self.system.logger.debug('SetStatus(%s, %s) by %s', obj, value, caller)
            try:
                obj.set_status(value, origin=caller, force=force)
            except ValueError as e:
                self.system.logger.error(
                    'Trying to set invalid status %s of type %s (by %s). Error: %s', value, type(value), caller, e)
            except AttributeError as e:
                self.system.logger.error(
                    'Trying to set status of invalid object %s of type %s, by %s. Error: %s', obj, type(obj), caller, e)
        return True

    def _give_triggers(self):
        return self.value

    def _give_targets(self):
        return self.obj


class SetAttr(AbstractAction):

    """Set object's attributes

       Usage::

            SetAttr(obj, attr=value, attr2=value2)
            # performs setattr(obj, attr, value) and setattr(obj, attr2, value2).
    """

    def __init__(self, obj, **kwargs):
        super(SetAttr, self).__init__(obj, **kwargs)

    def call(self, caller, **kwargs):
        if not caller:
            return
        obj = self.obj
        for attr, val in list(self._kwargs.items()):
            val = self.call_eval(val, caller, **kwargs)
            setattr(obj, attr, val)
        return True

    def _give_triggers(self):
        return list(self._kwargs.values())

    def _give_targets(self):
        return self.obj


class Changed(AbstractCallable):

    """
        Is value changed since evaluated last time? If this is the first time this Callable
        is called (i.e. comparison to last value cannot be made), return True.

        Usage::

            Changed(sensor1)
    """
    _lastval = Any(transient=True)

    def call(self, caller, **kwargs):
        if not caller:
            return
        with self._lock:
            newval = self.call_eval(self.obj, caller, **kwargs)
            rval = self._lastval != newval
            self.logger.debug("Changed(%s) last:%s new:%s: rval:%s", caller, self._lastval, newval, rval)
            self._lastval = newval
            return rval

    def _give_targets(self):
        return None


class Swap(AbstractAction):

    """
        Swap sensor or BinaryActuator status (False to True and True to False)

        Usage::

            Swap(actuator1)
    """

    def call(self, caller, trigger=None, **kwargs):
        if not caller:
            return
        rv = not (self.call_eval(self.obj, caller, **kwargs))
        self.logger.debug("Swap(%s): rv:%s", caller, rv)
        if trigger == self.obj:
            self.logger.debug('Swap: ignoring setting trigger value')
            return False
        self.obj.set_status(rv, caller)
        return rv

    def _give_triggers(self):
        return None


class AbstractRunner(AbstractAction):

    """ Abstract baseclass for Callables that are used primarily to run other Actions """


class Run(AbstractRunner):

    """Run specified Callables one at time. Return always True.

    Usage::

        Run(callable1, callable2, ...)
    """

    def call(self, caller=None, **kwargs):
        if not caller:
            return
        for i in self.objects:
            self.call_eval(i, caller, **kwargs)
        return True


class Delay(AbstractRunner):

    """Execute commands delayed by time (in seconds) in separate thread

    Usage::

        Delay(delay_in_seconds, action)
    """

    @property
    def delay(self):
        return self._args[0]

    @property
    def objects(self):
        return self._args[1:]

    def call(self, caller, **kwargs):
        if not caller:
            return

        with self._lock:
            state = self.get_state(caller)

            timers = state.get_or_create('timers', [])

            self.logger.info("Scheduling %s", self)
            delay = self.call_eval(self.delay, caller, **kwargs)
            timer = threading.Timer(delay, None)
            timer.function = threaded(self._run, caller, timer, **kwargs)
            time_after_delay = datetime.datetime.now() + datetime.timedelta(seconds=delay)
            timer.name = "Timer for %s timed at %s (%d sek)" % (self, time_after_delay, delay)
            timer.start()
            timers.append(timer)

    def cancel(self, caller):
        with self._lock:
            state = self.get_state(caller)
            timers = state.get('timers', [])

            for timer in timers:
                if timer.is_alive():
                    self.logger.info("Cancelling %s", self)
                    timer.cancel()
            self.del_state(caller)

        super(Delay, self).cancel(caller)

    def _run(self, caller, timer, **kwargs):
        self.logger.info("Time is up, running %s", self)
        for i in self.objects:
            if not caller in self.state:
                # cancelled
                return
            self.call_eval(i, caller, **kwargs)

        with self._lock:
            if caller in self.state: # if not cancelled
                self.get_state(caller).timers.remove(timer)
        return True


class Threaded(Delay):

    """Execute commands in a single thread (in order)

    Usage::

        Threaded(action)

    """

    def __init__(self, *args, **kwargs):
        super(Threaded, self).__init__(0, *args, **kwargs)


class If(AbstractCallable):

    """Basic If statement

    Usage::

        If(x, y, z) # if x, then run y, z, where x, y, and z are Callables or StatusObjects
        If(x, y)

    """

    def call(self, caller=None, **kwargs):
        if self.call_eval(self.objects[0], caller, **kwargs):
            objs = self.objects[1:]
            if len(objs) > 1:
                for i in objs:
                    self.call_eval(i, caller, **kwargs)
                return True
            else:
                return self.call_eval(self.objects[1], caller, **kwargs)
        else:
            return False

    def _give_triggers(self):
        return self.objects[1:]

    def _give_targets(self):
        return self.objects[1:]


class IfElse(AbstractCallable):

    """
    Basic if - then - else statement

    Usage::

        IfElse(x, y, z) # if x, then run y, else run z, where x, y,
                        # and z are Callables or StatusObjects
        IfElse(x, y)
    """

    def call(self, caller=None, **kwargs):
        if self.call_eval(self.objects[0], caller, **kwargs):
            return self.call_eval(self.objects[1], caller, **kwargs)
        if len(self.objects) > 2:
            return self.call_eval(self.objects[2], caller, **kwargs)
        else:
            return False

    def _give_triggers(self):
        return self.objects[1:]

    def _give_targets(self):
        return self.objects[1:]


class Switch(AbstractCallable):

    """
    Basic switch - case statement.

    Two alternative usages:

    * First argument switch criterion (integer-valued) and others are cases **OR**
    * First argument is switch criterion and second argument is dictionary that contains all possible
      cases as keys and related actions as their values.

    Usage::

        Switch(criterion, choice1, choice2...) # where criteria is integer-valued
                                               # (Callable or StatusObject etc.)
                                               # and choice1, 2... are Callables.

        Switch(criterion, {'value1': callable1, 'value2': 'callable2'})
    """

    def call(self, caller=None, **kwargs):
        sel = self.call_eval(self.objects[0], caller, **kwargs)
        if isinstance(self.value, dict):
            return self.call_eval(self.value.get(sel, None), caller, **kwargs)
        else:
            return self.call_eval(self.objects[sel + 1], caller, **kwargs)

    def _give_targets(self):
        return deep_iterate(self.objects[1:])

    def _give_triggers(self):
        return deep_iterate(self.objects[1:])


class TryExcept(AbstractRunner):

    """Try returning `x`, but if exception occurs in the value evaluation, then return `y`.

    Usage::

        Try(x, y) # where x and y are Callables or StatusObjects etc.
    """

    def call(self, caller=None, **kwargs):
        try:
            return self.call_eval(self.objects[0], caller, **kwargs)
        except:
            return self.call_eval(self.objects[1], caller, **kwargs)


class AbstractMathematical(AbstractCallable):

    def _give_targets(self):
        return None


class Min(AbstractMathematical):

    """
    Give minimum number of given objects.

    Usage::

        Min(x, y, z...)
        # where x,y,z are anything that can be
        # evaluated as number (Callables, Statusobjects etc).
     """

    def call(self, caller=None, **kwargs):
        val = float("inf")
        for i in self.objects:
            val = min(val, self.call_eval(i, caller, **kwargs))
        return val


class Max(AbstractMathematical):

    """Give maximum number of given objects

    Usage::

        Max(x, y, z...)
        # where x,y,z are anything that can be
        # evaluated as number (Callables, Statusobjects etc).
    """

    def call(self, caller=None, **kwargs):
        val = -float("inf")
        for i in self.objects:
            val = max(val, self.call_eval(i, caller, **kwargs))
        return val


class Sum(AbstractMathematical):

    """Give sum of given objects

    Usage::

        Sum(x, y, z...)
        # where x,y,z are anything that can be
        # evaluated as number (Callables, Statusobjects etc).
    """

    def call(self, caller=None, **kwargs):
        _sum = 0.0
        for i in self.objects:
            _sum += self.call_eval(i, caller, **kwargs)
        return _sum


class Product(AbstractMathematical):

    """Give product of given objects

    Usage::

        Product(x, y, z...)
        # where x,y,z are anything that can be
        # evaluated as number (Callables, Statusobjects etc).

    """

    def call(self, caller=None, **kwargs):
        _sum = 1.0
        for i in self.objects:
            _sum *= self.call_eval(i, caller, **kwargs)
        return _sum


class Mult(Product):

    """Synonym of Product"""


class Add(Sum):

    """Synonym of Sum """


class AbstractLogical(AbstractMathematical):

    """Abstract class for logic operations (:class:`.And`, :class:`.Or` etc.) """


class Anything(AbstractLogical):

    """ Condition which gives `True` always

    Usage::

        Anything(x,y,z...)
    """

    def call(self, caller=None, **kwargs):
        return True


class Or(AbstractLogical):

    """ Or condition

    Usage::

        Or(x,y,z...) # gives truth value of x or y or z or ,,,
    """

    def call(self, caller=None, **kwargs):
        def _or(list):
            for i in list:
                val = self.call_eval(i, caller, **kwargs)
                if is_iterable(val):
                    val = _or(val)
                if val:
                    return True
            return False

        return _or(self.objects)


class And(AbstractLogical):

    """And condition

    Usage::

        And(x,y,z...) # gives truth value of x and y and z and ...

    """

    def call(self, caller=None, **kwargs):
        def _and(list):
            for i in list:
                val = self.call_eval(i, caller, **kwargs)
                if is_iterable(val):
                    val = _and(val)
                if not val:
                    return False
            return True
        return _and(self.objects)


class Neg(AbstractLogical):

    """Give negative of specified callable (minus sign)

    Usage::

        Neg(x) # returns -x
    """

    def call(self, caller=None, **kwargs):
        assert len(self.objects) == 1, 'Too many arguments'
        return -self.call_eval(self.obj, caller, **kwargs)


class Not(AbstractLogical):

    """Give negation of specified object

    Usage::

        Not(x) # returns not x
    """

    def call(self, caller=None, **kwargs):
        assert len(self.objects) == 1, 'Too many arguments'
        return not self.call_eval(self.obj, caller, **kwargs)


class Equal(AbstractLogical):

    """Equality condition, i.e. is x == y

    Usage::

        Equal(x, y) # returns truth value of x == y
    """

    def call(self, caller=None, **kwargs):
        return self.call_eval(self.obj, caller, **kwargs) == self.call_eval(self.value, caller, **kwargs)


class Less(AbstractLogical):

    """Condition: is x < y

    Usage::

        Less(x,y) # returns truth value of x < y
    """

    def call(self, caller=None, **kwargs):
        a = self.call_eval(self.obj, caller, **kwargs)
        b = self.call_eval(self.value, caller, **kwargs)
        try:
            rv = a < b
        except TypeError:
            rv = False
        return rv

class More(AbstractLogical):

    """Condition: is x > y

    Usage::

        More(x,y) # returns truth value of x > y

    """

    def call(self, caller=None, **kwargs):
        a = self.call_eval(self.obj, caller, **kwargs)
        b = self.call_eval(self.value, caller, **kwargs)
        try:
            rv = a > b
        except TypeError:
            rv = False
        return rv


class Value(AbstractLogical):

    """Give specified value

    Usage::

        Value(x) # returns value of x. Used to convert StatusObject into Callable,
                 # for example, if StatusObject status needs to be used directly
                 # as a condition of Program condition attributes.

    """
    _args = CList

    def call(self, caller=None, **kwargs):
        return self.call_eval(self.obj, caller, **kwargs)


class AbstractQuery(AbstractCallable):

    """
    Baseclass for query type of Callables, i.e. those that return
    set of objects from system based on given conditions.
    """


class ReprObject(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


class OfType(AbstractQuery):

    """
    Gives all objects of given type that are found in System

    Usage & example::

        OfType(type, **kwargs)
        OfType(AbstractActuator, exclude=['actuator1', 'actuator2'])
        # returns all actuators in system, except those named 'actuator1' and 'actuator2'.

    :param list exclude: list of instances to be excluded from the returned list.

    """

    system_objects_changed = Event
    triggers = Property(trait=Set(trait=StatusObject),
                        depends_on='on_setup_callable, _kwargs_items, _args_items, system_objects_changed')

    targets = Property(trait=Set(trait=StatusObject),
                       depends_on='on_setup_callable, _kwargs, _kwargs_items, _args, _args_items, '
                                  'system_objects_changed')

    setup_complete = CBool(transient=True)

    @on_trait_change('system')
    def set_setup_complete(self, name, new):
        if name == 'system':
            self.system.on_trait_change(self.set_setup_complete, 'post_init_trigger')
        if name == 'post_init_trigger':
            self.setup_complete = True

    @on_trait_change('system.objects, system.objects_items, setup_complete')
    def trigger_system_objects_changed(self):
        if self.setup_complete:
            self.system_objects_changed = 1

    def _both(self):
        if not self.system:
            return set()
        exclude = set(self._kwargs.get('exclude', []))  # exclude must be list type
        return {i for i in self.system.objects if isinstance(i, tuple(self.objects))} - exclude

    @cached_property
    def _get_triggers(self):
        if self._kwargs.get('type', 'both') in ['triggers', 'both']:
            return self._both()
        return set()

    @cached_property
    def _get_targets(self):
        if self._kwargs.get('type', 'both') in ['targets', 'both']:
            return self._both()
        return set()

    def call(self, caller=None, **kwargs):
        return self.targets

    def give_str(self):
        args = [ReprObject(i.__name__) for i in self.objects]
        return self._give_str(args, self._kwargs)

    def give_str_indented(self, tags=False):
        args = [ReprObject(i.__name__) for i in self.objects]
        return self._give_str_indented(args, self._kwargs, tags)


class RegexSearch(AbstractCallable):

    """
    Scan through string looking for a match to the pattern.
    Return matched parts of string by :func:`re.search`.

    :param int group: Match group can be chosen by group number.

    Usage & examples::

        RegexSearch(match_string, content_to_search, **kwargs)

        RegexSearch(r'(\d*)(\w*)', '12test')          # returns '12'
        RegexSearch(r'(\d*)(\w*)', '12test', group=2) # returns 'test'
        RegexSearch(r'testasfd', 'test')              # returns ''

    .. tip::
        More examples in unit tests

    """

    def call(self, caller=None, **kwargs):
        pattern = str(self.call_eval(self.obj, caller, **kwargs))
        searchstring = str(self.call_eval(self.value, caller, **kwargs))
        match = re.search(pattern, searchstring, re.MULTILINE)
        if match:
            return match.group(self._kwargs.get('group', 1))
        else:
            return ''


class RegexMatch(AbstractCallable):

    """
    Try to apply the pattern at the start of the string.
    Return matched parts of string by :func:`re.match`.

    :param int group: Match group can be chosen by group number.

    Usage & examples from unit tests::

        RegexMatch(match_string, content_to_search, **kwargs)

        RegexMatch(r'heptest', 'heptest')                # returns 'heptest'
        RegexMatch(r'heptest1', 'heptest')               # returns ''
        RegexMatch(r'(hep)te(st1)', 'heptest1', group=1) # returns 'hep'
        RegexMatch(r'(hep)te(st1)', 'heptest1', group=2) # returns 'st1'

    .. tip::
        More examples in unit tests

    """

    def call(self, caller=None, **kwargs):
        pattern = self.call_eval(self.obj, caller, **kwargs)
        searchstring = self.call_eval(self.value, caller, **kwargs)
        match = re.match(pattern, searchstring, re.MULTILINE)
        if match:
            return match.group(self._kwargs.get('group', 0))
        else:
            return ''



class RemoteFunc(AbstractCallable):

    """
        Evaluate remote function via XMLRPC.

        Usage::

            RemoteFunc('host', 'funcname', *args, **kwargs)
    """
    _cached_server = Any(transient=True)

    def call(self, caller, **kwargs):
        try:
            if self._cached_server is None:
                host = self.call_eval(self.obj, caller, **kwargs)
                self._cached_server = server = xmlrpc.client.ServerProxy(host)
            else:
                server = self._cached_server

            funcname = self.call_eval(self.value, caller, **kwargs)
            args = [self.call_eval(o, caller, **kwargs) for o in self.objects[2:]]
            _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
            try:
                return getattr(server, funcname)(*args, **_kwargs)
            except (xmlrpc.client.Fault, HTTPException) as e:
                self.logger.exception(
                    'Exception occurred in remote function call (%s,%s)(*%s, **%s), error: %s', server, funcname, args, _kwargs, e)
        except (socket.gaierror, IOError, xmlrpc.client.Fault) as e:
            self.logger.error('Could call remote function, error: %s', e)


class WaitUntil(AbstractRunner):

    """
        Wait until sensor/actuator/callable status changes to True and then execute commands.
        WaitUntil will return immediately and only execute specified actions
        after criteria is fullfilled.

        Usage::

            WaitUntil(sensor_or_callable, Action1, Action2, etc)

        .. note::
            No triggers are collected from WaitUntil

    """

    def call(self, caller, **kwargs):
        obj = self.name_to_system_object(self.obj)

        def callback(**kwargs2):
            nocallback = kwargs2.get('nocallback', False)
            callbacks = self.get_state(caller).callbacks if not nocallback else []

            if obj.status and (nocallback or (callbacks and callback in callbacks)):
                for i in self.objects[1:]:
                    self.call_eval(i, caller, **kwargs)
                if not nocallback:
                    self.logger.debug('Removing executed callback')
                    with self._lock:
                        obj.on_trait_change(callback, 'status', remove=True)
                        callbacks.remove(callback)
        if not obj.status:
            self.logger.debug('Adding callback')
            obj.on_trait_change(callback, 'status')
            with self._lock:
                callbacks = self.get_state(caller).get_or_create('callbacks', [])
                callbacks.append(callback)
        else:
            self.logger.debug('Calling directly, no callback')
            callback(nocallback=True)

    def cancel(self, caller):
        self.logger.debug('Cancelling callbacks')
        with self._lock:
            state = self.get_state(caller)
            callbacks = state.get('callbacks', [])
            for cb in callbacks:
                self.obj.on_trait_change(cb, 'status', remove=True)
            self.del_state(caller)
        super(WaitUntil, self).cancel(caller)

    def _give_triggers(self):
        return None


class While(AbstractRunner):

    """
        Executes commands (in thread) as long as criteria (sensor, actuator, callable status) remains true.
        Flushes worker queue between each iteration such that criteria is updated, if executed
        actions alter it.

        :param Callable do_after: given Callable is executed after while loop is finished.

        Usage & example::

            While(criteria, action1, action2, do_after=action3)

            # Example loop that runs actions 10 times. Assumes s=UserIntSensor()
            Run(
                SetStatus(s, 0),
                While(s < 10,
                    SetStatus(s, s+1),
                    other_actions
                )
            )

        .. note::
            While execution is performed in separate thread
        .. note::
            No triggers are collected from While


    """

    class ExitThread(Exception):
        pass

    def _run(self, caller, thread, **kwargs):
        self.system.flush()
        try:
            while self.call_eval(self.obj, caller, **kwargs):
                for i in self.objects[1:]:
                    if thread._cancel_while:
                        raise self.ExitThread
                    self.call_eval(i, caller, **kwargs)
                self.system.flush()
            do_after = self._kwargs.get('do_after')
            if do_after:
                self.call_eval(do_after, caller, **kwargs)
        except self.ExitThread:
            self.logger.debug('While exited via cancel')

        with self._lock:
            state = self.get_state(caller)
            state.threads.remove(thread)
            if not state.threads:
                self.logger.debug('Last thread, removing state')
                self.del_state(caller)

    def call(self, caller, **kwargs):
        with self._lock:
            state = self.get_state(caller)
            threads = state.get_or_create('threads', [])
            t = threading.Timer(0., None)
            t.function = threaded(self._run, caller, t, **kwargs)
            t.name = 'Thread for %s' % self
            t._cancel_while = False
            threads.append(t)
            t.start()
        return True

    def cancel(self, caller):
        self.logger.debug('Canceling While')
        with self._lock:
            state = self.get_state(caller)
            for t in state.get('threads', []):
                t._cancel_while = True
        super(While, self).cancel(caller)

    def _give_triggers(self):
        return None


class TriggeredBy(OnlyTriggers):

    """
        Return whether action was triggered by one of specified triggers or not

        If no arguments, return the trigger.

        Usage::

            TriggeredBy() # -> returns the trigger
            TriggeredBy(trig1, trig2...) #-> Returns if trigger is one of arguments
    """

    def call(self, caller=None, trigger=None, **kwargs):
        if self.objects:
            obj_eval = [self.name_to_system_object(obj) for obj in self.objects]
            return trigger in obj_eval
        else:
            return trigger


__all__ = get_modules_all(AbstractCallable, locals())
