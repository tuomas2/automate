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
import logging
import operator
import threading
import time
import sys

import datetime
from traits.api import (cached_property, Any, CBool, Instance, Dict, Str, CFloat,
                        List, Enum, Bool, Property, Event)
from traits.trait_errors import TraitError

from automate.common import Lock, AbstractStatusObject, CompareMixin, nomutex
from automate.worker import StatusWorkerTask, DummyStatusWorkerTask
from automate.program import ProgrammableSystemObject, DefaultProgram
from automate.systemobject import SystemObject

if sys.version_info >= (3, 0):
    TimerClass = threading.Timer
else:
    TimerClass = threading._Timer


class StatusObject(AbstractStatusObject, ProgrammableSystemObject, CompareMixin):

    """
        Baseclass for Sensors and Actuators
    """

    editable = True

    #: Determines minimum time required for switching. State change is then delayed if necessary.
    safety_delay = CFloat(0.)

    #: Determines when :attr:`.safety_delay` needs to be taken into account: when status is
    #: rising, falling or both.
    safety_mode = Enum("rising", "falling", "both")

    #: Similar to :attr:`.safety_delay`, but just delays change to make sure that events shorter
    #: than change_delay are not taken into account
    change_delay = CFloat(0.)

    #: As :attr:`.safety_mode`, but for :attr:`.change_delay`
    change_mode = Enum("rising", "falling", "both")

    #: Do not emit actuator status changes into logs
    silent = CBool(False)

    #: Print more debugging information into logs
    debug = CBool(False)

    #: (property) Is delayed change taking place at the moment?
    changing = Property(trait=Bool, transient=True, depends_on='_timed_action, _queued_job')

    @cached_property
    def _get_changing(self):
        if self._queued_job or self._timed_action:
            return True
        return False

    # Thread of currently running action
    _timed_action = Instance(TimerClass, transient=True)

    # Reference of status change job that is in the worker queue is saved here
    _queued_job = Instance(StatusWorkerTask, transient=True)

    # Time when status was last changed
    _last_changed = CFloat

    # The time when last change started
    _change_start = CFloat(transient=True)

    # Lock that is acquired when changing the status
    _status_lock = Instance(Lock, transient=True)

    logger = Instance(logging.Logger, transient=True)

    view = ["name", "status", "description", "safety_delay",
            "safety_mode", "change_delay", "change_mode"] + SystemObject.view

    simple_view = []

    # used by Web UI, for templates
    data_type = Str(transient=True)

    def __init__(self, *args, **kwargs):
        self._status_lock = Lock('statuslock')
        super(StatusObject, self).__init__(*args, **kwargs)

    def __setstate__(self, *args, **kwargs):
        self._status_lock = Lock('statuslock')
        super(StatusObject, self).__setstate__(*args, **kwargs)

    @property
    def is_program(self):
        """
            A property which can be used to check if StatusObject uses program features or not.
        """
        from automate.callables import Empty
        return not (isinstance(self.on_activate, Empty)
                    and isinstance(self.on_deactivate, Empty)
                    and isinstance(self.on_update, Empty))

    #: Status of the object.
    status = Property(depends_on="_status, _status_trigger", transient=True)

    #: To force trigger status change events even if status itself does not change
    _status_trigger = Event

    def get_status_display(self, **kwargs):
        """
            Define how status is displayed in UIs (add units etc.).
        """
        if 'value' in kwargs:
            value = kwargs['value']
        else:
            value = self.status

        return u"%s" % value

    def get_as_datadict(self):
        """
            Get data of this object as a data dictionary. Used by websocket service.
        """
        d = super(StatusObject, self).get_as_datadict()
        d.update(dict(status=self.status, data_type=self.data_type, editable=self.editable))
        return d

    @cached_property
    def _get_status(self):
        return self._status

    def _set_status(self, value):
        self.set_status(value)

    def setup_system(self, *args, **kwargs):
        super(StatusObject, self).setup_system(*args, **kwargs)
        self.data_type = self._status.__class__.__name__

    def set_status(self, new_status, origin=None, force=False):
        """
            For sensors, this is synonymous to::

                sensor.status = new_status

            For (non-slave) actuators, origin argument (i.e. is the program that is
            changing the status) need to be given,
        """
        raise NotImplementedError

    def update_status(self):
        """
           In sensors: implement particular value reading from device etc. here (this calls set_status(value)).
           In actuators: set value in particular device.
           Implement in subclasses.
        """

    def activate_program(self, program):
        """
            When program controlling this object activates, it calls this function.
        """

    def deactivate_program(self, program):
        """
            When program controlling this object deactivates, it calls this function.
        """

    def get_program_status(self, program):
        """
            Determine status of this object set by a particular program.
            Useful only for Actuators but defined here for interface compatibility.
        """
        return self.status

    def _set_real_status(self, status, prog):
        # _status_lock is acquired at StatusWorkerTask. Do not call this function from anywhere else!
        # This function is finally called by queue and this sets the value as desired.
        # Thus no need to worry that this function would be called in two threads
        # simultaneously (caller always WorkerThread).
        # prog is always None for non-actuators

        self.logger.debug('_set_real_status %s', status)
        if not self.silent:
            if isinstance(self, AbstractActuator):
                self.logger.info(u"%s %s (by %s) setting status to %s", self.__class__.__name__, self, prog, status)

        # if not self.slave and prog != getattr(self, 'program', None):
        if not getattr(self, 'slave', True) and not prog is getattr(self, 'program', None):
            self.logger.debug('program had changed, not changing')
            return

        self._change_start = 0.
        self._last_changed = time.time()

        try:
            if self._status == status:
                self._status_trigger = True
            else:
                self._status = status
        except TraitError as e:
            self.logger.warning('Wrong type of status %s was passed to %s. Error: %s', status, self, e)

    def _add_statuschange_to_queue(self, status, prog, with_statuslock=False):
        # This function is used for delayed actions
        if self.system.two_phase_queue:
            with self._status_lock if with_statuslock else nomutex:
                if status != self._status:
                    self._queued_job = StatusWorkerTask(func=self._set_real_status, args=(status, prog), object=self)
                    self.system.worker_thread.put(self._queued_job)
        else:
            self.system.worker_thread.put(DummyStatusWorkerTask(self._set_real_status, status, prog))

    def _are_delays_active(self, new_status):
        try:
            mode = "rising" if new_status > self._status else "falling"
        except TypeError:
            # if we can not determine whether value is rising or falling, we'll assume it's rising
            mode = 'rising'
        safety_active = False
        change_active = False
        if self.safety_delay > 0. and self.safety_mode in [mode, "both"]:
            safety_active = True
        if self.change_delay > 0. and self.change_mode in [mode, "both"]:
            change_active = True
        return safety_active, change_active

    def _do_change_status(self, status, force=False):
        """
        This function is called by
           - set_status
           - _update_program_stack if active program is being changed
             - thia may be launched by sensor status change.
             status lock is necessary because these happen from different
             threads.

        This does not directly change status, but adds change request
        to queue.
        """
        self.system.worker_thread.put(DummyStatusWorkerTask(self._request_status_change_in_queue, status, force=force))

    @property
    def next_scheduled_action(self):
        return getattr(self._timed_action, 'next_action', None)

    def _request_status_change_in_queue(self, status, force=False):
        def timer_func(func, *args):
            func(*args)
            self._timed_action = None

        with self._status_lock:
            timenow = time.time()
            logger = self.logger.info if self.debug else self.logger.debug
            logger("_do_change_status prg:%s status:%s", getattr(self, 'program', None), status)

            if self._timed_action:
                if self._timed_action.is_alive():
                    logger("Cancelling previous safety/change_delay action. Now changing to %s", status)
                    self._timed_action.cancel()
                self._timed_action = None

            self._queued_job = None

            safetydelay_active, changedelay_active = self._are_delays_active(status)
            run_now = not (safetydelay_active or changedelay_active)

            if not self._change_start:
                self._change_start = timenow

            if status == self._status and not force:
                self._change_start = 0
                logger('Status same %s, no need to change', status)
                return

            orig_changedelay = self.change_delay if changedelay_active else 0
            safetydelay = self.safety_delay if safetydelay_active else 0

            changedelay = orig_changedelay - (timenow - self._change_start)

            if changedelay < 0:
                changedelay = orig_changedelay

            if run_now or (changedelay <= 0. and (timenow - self._last_changed > safetydelay)):
                logger("Adding status change to queue, about to change status to %s", status)
                if self.system.two_phase_queue:
                    self._add_statuschange_to_queue(status, getattr(self, "program", None))
                else:
                    self._set_real_status(status, getattr(self, 'program', None))

            else:
                timesince = time.time() - self._last_changed
                delaytime = max(0, safetydelay - timesince, changedelay)
                time_after_delay = datetime.datetime.now() + datetime.timedelta(seconds=delaytime)
                logger("Scheduling safety/change_delay timer for %f sek. Now %s. Going to change to %s.",
                       delaytime, self._status, status)
                self._timed_action = threading.Timer(delaytime, timer_func,
                                                     args=(self._add_statuschange_to_queue, status, getattr(self, "program", None), True))
                self._timed_action.name = "Safety/change_delay for %s timed at %s (%f sek)" % (self.name, time_after_delay, delaytime)
                self._timed_action.next_action = time_after_delay
                self._timed_action.start()
                return False


class AbstractSensor(StatusObject):

    """ Base class for all sensors """

    #: Is sensor user-editable in UIs. This variable is meant for per-instance tuning for Sensors,
    #: whereas :attr:`.editable` is for per-class adjustment.
    user_editable = CBool(False)

    #: Status type is defined as _status, but always use :attr:`.status` property to set/get values.
    _status = Any

    #: Default value for status
    default = Any

    #: If non-zero, Sensor status will be reset to default after defined time (in seconds).
    reset_delay = CFloat

    _reset_timer = Any(transient=True)

    #: Do not log status changes
    silent = CBool(False)

    view = StatusObject.view + ['default', 'name', 'tags', 'reset_delay']
    simpleview = StatusObject.simple_view + ['_status']

    def get_as_datadict(self):
        d = super(AbstractSensor, self).get_as_datadict()
        d.update(dict(user_editable=self.user_editable))
        return d

    def _setup_reset_delay(self):
        if self.reset_delay:
            if self._reset_timer and self._reset_timer.is_alive():
                self._reset_timer.cancel()
            self._reset_timer = threading.Timer(self.reset_delay, lambda: self.set_status(self.default))
            self._reset_timer.start()

    def set_status(self, status, origin=None, force=False):
        """
            Compatibility to actuator class.
            Also :class:`~automate.callables.builtin_callables.SetStatus`
            callable can be used for sensors too, if so desired.
        """

        if status != self.default:
            self._setup_reset_delay()
        return self._do_change_status(status, force)

    def update_status(self):
        """A method to read and update actual status. Implement it in subclasses, if necessary"""

    def _status_changed(self):
        if not self.silent:
            self.logger.info("status changed to %s", repr(self.status))

    def __str__(self):
        return self.name

    def setup_system(self, system, *args, **kwargs):
        name, traits = self._passed_arguments
        self.logger = logging.getLogger('automate.sensor')
        default = traits.get('default', None)
        super(AbstractSensor, self).setup_system(system, *args, **kwargs)
        if not default is None and not kwargs.get('loadstate', None):
            self.set_status(default)


class AbstractActuator(StatusObject):

    """ Base class for all actuators."""

    #: Default value for status. For actuators, this is set by automatically created
    #: :class:`~automate.program.DefaultProgram` dp_actuatorname
    default = Any(False, transient=True)

    #: If ``True``, actual status can be set by any program anytime without restrictions.
    slave = CBool

    #: A property giving current program governing the status of this actuator (program that has the highest priority)
    program = Property(trait=Instance(ProgrammableSystemObject), transient=True, depends_on="program_stack[]")

    #: This dictionary can be used to override program priorities.
    #:
    #: .. note::  Keys here must be program names, (not :class:`~automate.program.Program` instances).
    priorities = Dict(key_trait=Str, value_trait=CFloat)

    @cached_property
    def _get_program(self):
        try:
            return self.program_stack[-1]
        except IndexError:
            return

    #: Reference to actuators :class:`~automate.program.DefaultProgram`
    default_program = Instance(DefaultProgram)

    # Locks for thread-safety
    _actuator_status_lock = Instance(Lock, transient=True)

    _program_lock = Instance(Lock, transient=True)

    view = StatusObject.view + ["status", "slave", "tags"]
    simple_view = StatusObject.simple_view + ['status']

    def __init__(self, *args, **kwargs):
        self._actuator_status_lock = Lock("statuslock")
        self._program_lock = Lock("programlock")
        super(AbstractActuator, self).__init__(*args, **kwargs)

    def __setstate__(self, *args, **kwargs):
        self._actuator_status_lock = Lock("statuslock")
        self._program_lock = Lock("programlock")
        return super(AbstractActuator, self).__setstate__(*args, **kwargs)

    def set_status(self, status, origin=None, force=False):
        """ For programs, to set current status of the actuator. Each
            active program has its status in :attr:`.program_stack`
            dictionary and the highest priority is realized in the actuator """

        if not self.slave and origin not in self.program_stack:
            raise ValueError('Status cannot be changed directly')

        with self._actuator_status_lock:
            self.logger.debug("set_status got through, program: %s", origin)
            if self.debug:
                self.logger.info("Set_status %s %s %s", self.name, origin, status)

            if self.slave:
                return self._do_change_status(status, force)

            self.logger.debug("Sets status %s for %s", status, origin.name)

            with self._program_lock:
                self.program_status[origin] = status

                if self.program == origin:
                    return self._do_change_status(status, force)

    def activate_program(self, program):
        """
            Called by program which desires to manipulate this actuator, when it is activated.
        """
        self.logger.debug("activate_program %s", program)
        if program in self.program_stack:
            return

        with self._program_lock:
            self.logger.debug("activate_program got through %s", program)
            self.program_stack.append(program)
            self._update_program_stack()

    def deactivate_program(self, program):
        """
            Called by program, when it is deactivated.
        """
        self.logger.debug("deactivate_program %s", program)

        with self._program_lock:
            self.logger.debug("deactivate_program got through %s", program)
            if program not in self.program_stack:
                import ipdb
                ipdb.set_trace()
            self.program_stack.remove(program)
            if program in self.program_status:
                del self.program_status[program]
            self._update_program_stack()

    def update_program_stack(self):
        """
            Update :attr:`.program_stack`. Used by programs
            :attr:`~automate.program.ProgrammableSystemObject._priority_changed` attribute to reset ordering.
        """
        with self._program_lock:
            self._update_program_stack()

    def get_program_status(self, prog):
        """
            Give status defined by given program ``prog``
        """
        try:
            return self.program_status[prog]
        except KeyError:
            return None

    def _status_changed(self):
        """
            Override this method to whatever action you want to actualize when
            status is changed. This one is called in the initialization procedure as well.

            Usually this method is enough. Sometimes you might not want to do anything
            in the initialization, and then you can override __status_changed method instead.
        """

    # Private attributes

    #: Use property 'status' instead in normal operations (status is set via status worker thread).
    _status = Any(transient=True)

    #: Program stack of current programs, sorted automatically by program priority.
    program_stack = List(trait=Instance(ProgrammableSystemObject), transient=True)

    #: Dictionary containing statuses set by each active program
    program_status = Dict(key_trait=Instance(ProgrammableSystemObject), transient=True)

    def setup_system(self, system, *args, **kwargs):
        from automate.callables import SetStatus, Value, Empty
        super(AbstractActuator, self).setup_system(system, *args, **kwargs)
        actevent = SetStatus(self, Value(self.default))
        if self.slave:
            actevent = Empty()
            self.status = self.default

        from .program import DefaultProgram

        if not self.default_program:
            self.default_program = DefaultProgram(
                targets=[self],
                active_condition=Value(False),
                on_activate=actevent,
                priority=0,
                system=self.system,
                name='dp_%s' % self.name,
            )

            self.default_program.active_condition = Value(True)

        self._program_lock.name = "programlock " + self.name
        self._actuator_status_lock.name = "statuslock " + self.name

    def __str__(self):
        return self.name

    def _update_program_stack(self):
        # Use of this function must be protected from outside by self.program_lock!
        if self.priorities:
            self.program_stack.sort(key=lambda x: self.priorities.get(x.name, x.priority))
        else:
            self.program_stack.sort(key=operator.attrgetter('priority'))
        if self.program in self.program_status:
            self._do_change_status(self.program_status[self.program])
