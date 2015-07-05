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
# http://tuomasairaksinen.fi/automate/gospel/

"""
    Module for various Sensor classes.
"""

import time
import socket
import logging
import subprocess
import types
import pyinotify
import threading
import Queue

from croniter import croniter
from traits.api import Any, CInt, CFloat, Unicode, CUnicode, List, CBool, Instance, CStr, Int

from automate.common import get_modules_all
from automate.common import threaded, Lock
from automate.statusobject import AbstractSensor
from automate.callables import Value
from automate.callable import AbstractCallable

logger = logging.getLogger('automate.sensor')


class UserAnySensor(AbstractSensor):

    """User editable sensor type that accepts values of any types"""
    user_editable = CBool(True)
    _status = Any


class UserBoolSensor(AbstractSensor):

    """Boolean-valued user-editable sensor"""
    user_editable = CBool(True)
    _status = CBool


class UserEventSensor(UserBoolSensor):

    """
        Boolean-valued user-editable sensor suitable for using for singular events.

        After status has been changed to True, it changes automatically its status
        back to False.
    """

    def __status_changed(self):
        self.status = False

    def get_default_callables(self):
        callables = super(UserEventSensor, self).get_default_callables()
        callables['active_condition'] = Value(self)
        return callables


class AbstractNumericSensor(AbstractSensor):

    """
        Abstract class for numeric sensor types, that allows limiting
        value within a specific range.

        If limiting values (value_min, value_max) are used, value that exceeds
        these limits, is clipped to the range.
    """

    #: Minimum allowed value for status
    value_min = CFloat(float('-inf'))

    #: Maximum allowed value for status
    value_max = CFloat(float('inf'))

    view = AbstractSensor.view + ['value_min', 'value_max']

    @property
    def is_finite_range(self):
        return self.value_max - self.value_min < float('inf')

    def get_as_datadict(self):
        d = super(AbstractNumericSensor, self).get_as_datadict()
        d.update(dict(value_min=self.value_min, value_max=self.value_max))
        return d

    def set_status(self, status, origin=None):
        if status is None:
            clipped_status = None
        else:
            clipped_status = max(min(float(status), self.value_max), self.value_min)
        super(AbstractNumericSensor, self).set_status(clipped_status, origin)


class UserIntSensor(AbstractNumericSensor):

    """Integer-valued user-editable sensor"""
    user_editable = CBool(True)
    _status = CInt(0)


class UserFloatSensor(AbstractNumericSensor):

    """Float-valued user-editable sensor"""
    user_editable = CBool(True)
    _status = CFloat
    silent = CBool(True)


class UserStrSensor(AbstractSensor):

    """String-valued user-editable sensor"""
    user_editable = CBool(True)
    _status = CUnicode


class CronTimerSensor(AbstractSensor):

    """
        Scheduled start/stop timer. Both start and stop times
        are configured by cron-type string (see man 5 crontab for description of the
        definition format).
    """
    class CronListStr(Unicode):

        """Validation class for cron-compatible strings (for timers)"""

        def validate(self, object, name, value):
            vals = value.split(";")
            for v in vals:
                try:
                    c = croniter(v)
                except:
                    self.error(object, name, value)
                    return
            return value

    _status = CBool(False)

    #: Semicolon separated lists of cron-compatible strings that indicate
    #: when to switch status to True
    timer_on = CronListStr

    #: Semicolon separated lists of cron-compatible strings that indicate
    #: when to switch status to False
    timer_off = CronListStr

    # Cronit objects
    _cronit_on = List(transient=True)
    _cronit_off = List(transient=True)

    _timer_on = Any(transient=True)
    _timer_off = Any(transient=True)

    _timerlock = Any(transient=True)

    view = UserBoolSensor.view + ["timer_on", "timer_off"]

    def setup_system(self, *args, **traits):
        self._timerlock = Lock()
        super(CronTimerSensor, self).setup_system(*args, **traits)
        self._setup_timer_on()
        self._setup_timer_off()
        self.update_status()

    def update_status(self):
        with self._timerlock:
            if not (self._cronit_on and self._cronit_off):
                return
            from copy import deepcopy

            onprev = sorted(deepcopy(self._cronit_on), key=lambda x: x.get_prev())[-1].get_current()
            offprev = sorted(deepcopy(self._cronit_off), key=lambda x: x.get_prev())[-1].get_current()
            self.status = onprev > offprev

    def _switch_on(self):
        self.status = 1
        with self._timerlock:
            self._cronit_on[0].get_next()
        self._setup_timer_on()

    def _switch_off(self):
        self.status = 0
        with self._timerlock:
            self._cronit_off[0].get_next()
        self._setup_timer_off()

    def _timer_on_changed(self, name, new):
        with self._timerlock:
            self._cronit_on = [croniter(i, time.time()) for i in new.split(";")]
            for i in self._cronit_on:
                i.get_next()
        self._setup_timer_on()
        self.update_status()

    def _timer_off_changed(self, name, new):
        self._cronit_off = [croniter(i, time.time()) for i in new.split(";")]
        for i in self._cronit_off:
            i.get_next()
        self._setup_timer_off()
        self.update_status()

    def _setup_timer_on(self):
        with self._timerlock:
            if self._timer_on and self._timer_on.is_alive():
                self._timer_on.cancel()
            if not self._cronit_on:
                return

            self._cronit_on.sort(key=lambda x: x.get_current())
            delay = self._cronit_on[0].get_current() - time.time()
            self._timer_on = threading.Timer(delay, threaded(self._switch_on,))
            self._timer_on.name = "Timer for TimerSensor:on " + self.name.encode(
                "utf-8") + " at %s" % time.strftime("%a %T %D", time.localtime(time.time() + delay))
            self._timer_on.start()

    def _setup_timer_off(self):
        with self._timerlock:
            if self._timer_off and self._timer_off.is_alive():
                self._timer_off.cancel()
            if not self._cronit_on:
                return
            self._cronit_off.sort(key=lambda x: x.get_current())
            delay = self._cronit_off[0].get_current() - time.time()
            self._timer_off = threading.Timer(delay, threaded(self._switch_off))
            self._timer_off.name = "Timer for TimerSensor:off " + self.name.encode(
                "utf-8") + " at %s" % time.strftime("%a %T %D", time.localtime(time.time() + delay))
            self._timer_off.start()

    def cleanup(self):
        with self._timerlock:
            if self._timer_off:
                self._timer_off.cancel()
            if self._timer_on:
                self._timer_on.cancel()


class FileChangeSensor(AbstractSensor):

    """ Sensor that detects file changes on filesystem.
        Integer valued status is incremented by each change.
    """
    _status = CInt(0)

    #: Name of file or directory to monitor
    filename = CUnicode

    #: PyInotify flags to configure what file change events to monitor
    watch_flags = Int(pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_DELETE)

    _notifier = Any(transient=True)

    class InotifyEventHandler(pyinotify.ProcessEvent):

        def __init__(self, func, *args, **kwargs):
            self.func = func
            super(FileChangeSensor.InotifyEventHandler, self).__init__(*args, **kwargs)

        def process_default(self, event):
            self.func()

    def notify(self):
        self.status += 1

    def setup(self):
        if self._notifier:
            self._notifier.stop()
        wm = pyinotify.WatchManager()
        handler = self.InotifyEventHandler(self.notify)
        self._notifier = pyinotify.ThreadedNotifier(wm, default_proc_fun=handler)

        wm.add_watch(self.filename, self.watch_flags, rec=True)
        self._notifier.start()

    def cleanup(self):
        self._notifier.stop()


class AbstractPollingSensor(AbstractSensor):

    """ Abstract baseclass for sensor that polls periodically its status"""

    #: How often to do polling
    interval = CFloat(5)

    #: This can be used to enable/disable polling
    poll_active = CBool(True)

    _stop = CBool(False, transient=True)
    _pollthread = Any(transient=True)
    view = AbstractSensor.view + ["interval"]
    silent = CBool(True)

    def setup(self):
        self._restart()

    def _poll_active_changed(self, old, new):
        if not self.traits_inited():
            return
        if new:
            self._restart()
        else:
            self._pollthread.cancel()

    def _restart(self):
        if self._stop:
            return
        if self._pollthread and self._pollthread.is_alive():
            self._pollthread.cancel()
        if self.poll_active:
            self.update_status()
            self._pollthread = threading.Timer(self.interval, threaded(self._restart))
            self._pollthread.name = "PollingSensor: " + self.name.encode("utf-8") + " %.2f sek" % self.interval
            self._pollthread.start()

    def update_status(self):
        pass

    def cleanup(self):
        if self._pollthread:
            self._stop = True
            self._pollthread.cancel()


class PollingSensor(AbstractPollingSensor):

    """
        Polling sensor that uses a Callable when setting the status of the sensor.
    """

    #: Return value of this Callable is used to set the status of the sensor when polling
    status_updater = Instance(AbstractCallable)

    #: If set, typeconversion to this is used. Can be any function or type.
    type = Any

    callables = AbstractPollingSensor.callables + ['status_updater']

    def get_default_callables(self):
        from automate.callables import Empty
        c = super(PollingSensor, self).get_default_callables()
        c['status_updater'] = Empty()
        return c

    def setup(self):
        self.status_updater.setup_callable_system(self.system)
        self.on_trait_change(lambda: self.status_updater.setup_callable_system(self.system), 'status_updater')
        super(PollingSensor, self).setup()

    def update_status(self):
        if self.type is None:
            self.status = self.status_updater.call(self)
        else:
            self.status = self.type(self.status_updater.call(self))


class IntervalTimerSensor(AbstractPollingSensor):

    """
        Sensor that switches status between True and False periodically.
    """

    _status = CFloat

    def update_status(self):
        self.status = False if self.status else True


class SocketSensor(AbstractSensor):

    """
        Sensor that reads a TCP socket.

        Over TCP port, it reads data per lines and tries to set the status of the sensor
        to the value specified by the line. If content of the line is 'close', then connection
        is dropped.
    """

    #: Hostname/IP to listen. Use 0.0.0.0 to listen all interfaces.
    host = CStr('0.0.0.0')

    #: Port to listen
    port = CInt

    stop = CBool(transient=True)
    _socket = Instance(socket.socket, transient=True)
    _status = CInt

    def listen_loop(self):
        while not self.stop:
            try:
                self.logger.info('%s listening to connections in port %s', self.name, self.port)
                self._socket.listen(1)
                self._socket.settimeout(1)
                while not self.stop:
                    try:
                        conn, addr = self._socket.accept()
                    except socket.timeout:
                        continue
                    break
                self.logger.info('%s connected from %s', self.name, addr)
                conn.settimeout(1)
                while not self.stop:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break
                        self.status = int(data.strip())
                        conn.sendall('OK\n')
                    except socket.timeout:
                        data = ''
                    except ValueError:
                        if data.strip() == 'close':
                            break
                        conn.sendall('NOK\n')
            except socket.error as e:
                self.logger.info("%s: Error %s caught.", self, e)
            except:
                if self.stop:
                    return
                else:
                    raise
            conn.close()
            self.logger.info('%s: connection %s closed', self.name, addr)
        self._socket.close()

    def setup(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self.port))
        t = threading.Thread(target=self.listen_loop, name='SocketSensor %s' % self.name)
        t.start()

    def cleanup(self):
        self.stop = True


class ShellSensor(AbstractSensor):

    """
        Run a shell command and follow its output. Status is set according to output, which is
        filtered through custome filter function.
    """

    #: Command can be, for example, 'tail -f logfile.log', which is convenient approach to follow log files.
    cmd = CStr
    #: If this is set to true, caller object is passed to the filter function as second argument
    caller = CBool
    filter = Any
    """
        Filter function, which must be a generator, such as for example:

        .. code-block:: python

            def filter(queue):
                while True:
                    line = queue.get()
                    if line == 'EOF':
                        break
                    yield line

        or a simple line-by-line filter::

            def filter(line):
                return processed(line)
    """

    _simple = CBool
    _stop = CBool
    _queue = Any(transient=True)
    _process = Any(transient=True)

    def cmd_loop(self):
        p = self._process = subprocess.Popen(self.cmd, shell=True, executable='bash', stdout=subprocess.PIPE)
        while True:
            line = p.stdout.readline()
            self._queue.put(line)
            if not line:
                self.logger.debug('Process exiting (cmd_loop)')
                break

    def status_loop(self):
        args = (self,) if self.caller else ()

        def default_filter(queue, *args):
            while True:
                line = queue.get()
                if not line:
                    self.logger.debug('Process exiting (status_loop)')
                    break
                yield line

        def simple_filter(line, *args):
            return line

        # Let's test if filter is 'simple' or not
        if self.filter:
            tst = self.filter('test line')
            if not isinstance(tst, types.GeneratorType):
                self._simple = True

        if self._simple:
            filter = self.filter or simple_filter
            while True:
                line = self._queue.get()
                if not line:
                    self.logger.debug('Process exiting (status_loop)')
                    break
                self.status = filter(line, *args)

        else:
            filter = self.filter or default_filter
            for s in filter(self._queue, *args):
                if self._stop:
                    break

                self.status = s

    def setup(self):
        self._queue = Queue.Queue()
        t1 = threading.Thread(target=self.cmd_loop, name='ShellSensor.cmd_loop %s' % self.name)
        t1.start()
        t2 = threading.Thread(target=self.status_loop, name='ShellSensor.status_loop %s' % self.name)
        t2.start()
        self.logger.debug('Threads started')

    def cleanup(self):
        self._process.terminate()
        self.logger.debug('Process exiting (cleanup)')
        self._stop = True

__all__ = get_modules_all(AbstractSensor, locals())
