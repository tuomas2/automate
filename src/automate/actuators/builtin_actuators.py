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

"""
    Module for builtin Actuator classes
"""
from __future__ import division
from __future__ import unicode_literals

from threading import Thread
import time

from traits.api import Any, CBool, Instance, CInt, CFloat

from automate.common import threaded, get_modules_all
from automate.statusobject import AbstractActuator


class BoolActuator(AbstractActuator):

    """ Boolean valued actuator"""
    _status = CBool(transient=True)
    default = CBool


class IntActuator(AbstractActuator):

    """ Integer valued actuator"""
    _status = CInt(transient=True)
    default = CInt


class FloatActuator(AbstractActuator):

    """Floating point valued actuator"""
    _status = CFloat(transient=True)
    default = CFloat
    silent = CBool(True)


class AbstractInterpolatingActuator(FloatActuator):

    """
        Abstract base class for interpolating actuators.
    """
    #: How often to update status (as frequency)
    change_frequency = CFloat

    #: Slave actuator, that does the actual work (set .slave attribute to True in slave actuator)
    slave_actuator = Instance(AbstractActuator)

    _changethread = Any(transient=True)
    view = FloatActuator.view + ["change_frequency"]

    def _status_changed(self):
        if self._changethread and self._changethread.is_alive():
            return
        self._changethread = Thread(target=threaded(self.statuschanger),
                                    name="Changethread for " + self.name)
        self._changethread.start()


class ConstantSpeedActuator(AbstractInterpolatingActuator):

    """
        Change slave status with constant speed
    """

    #: Status change speed (change / second)
    speed = CFloat

    view = AbstractInterpolatingActuator.view + ["speed"]

    def statuschanger(self):
        if not self.slave_actuator:
            return
        while self.slave_actuator.status != self.status:
            delta = self.speed if self.status > self.slave_actuator.status else -self.speed
            newstatus = self.slave_actuator.status + delta / self.change_frequency
            if (delta > 0) == (newstatus > self.status) or abs(newstatus - self.status) < delta / self.change_frequency:
                self.slave_actuator.status = self.status
            else:
                self.slave_actuator.status = newstatus
            time.sleep(1. / self.change_frequency)


class ConstantTimeActuator(ConstantSpeedActuator):

    """
    Change slave status in constant time
    """

    #: Time that is needed for change
    change_time = CFloat

    view = ConstantSpeedActuator.view + ["change_time"]

    def _status_changed(self):
        self.speed = abs(self.slave_actuator.status - self.status) / self.change_time
        if self._changethread and self._changethread.is_alive():
            return
        self._changethread = Thread(target=threaded(self.statuschanger),
                                    name="Changethread for " + self.name)
        self._changethread.start()


__all__ = get_modules_all(AbstractActuator, locals())
