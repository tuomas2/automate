# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of automate-arduino.
#
# automate-arduino is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# automate-arduino is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with automate-arduino.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from traits.api import CInt, Instance, CBool, CFloat

from automate.actuators import FloatActuator
from automate.service import AbstractSystemService
from automate.statusobject import AbstractActuator


class AbstractArduinoActuator(AbstractActuator):

    """
        Abstract base class for Arduino actuators
    """

    #: Arduino device number (specify, if more than 1 devices configured in ArduinoService)
    dev = CInt(0)

    #: Arduino pin number
    pin = CInt

    _arduino = Instance(AbstractSystemService, transient=True)

    def setup(self, *args, **kwargs):
        super(AbstractArduinoActuator, self).setup(*args, **kwargs)
        self._arduino = self.system.request_service('ArduinoService')


class ArduinoDigitalActuator(AbstractArduinoActuator):

    """
        Boolean-valued actuator object for digital Arduino output pins
    """
    _status = CBool(transient=True)

    def setup(self, *args, **kwargs):
        super(ArduinoDigitalActuator, self).setup(*args, **kwargs)
        self._arduino.setup_digital(self.dev, self.pin)

    def _status_changed(self):
        self._arduino.change_digital(self.dev, self.pin, self._status)

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.dev, self.pin)


class ArduinoServoActuator(AbstractArduinoActuator):

    """
        Float-valued actuator object for Arduino output pins that can be configured in Servo mode
        Status is servo angle (0-360).
    """

    _status = CFloat(transient=True)

    #: Minimum pulse time (in microseconds)
    min_pulse = CInt(544)

    #: Maximum pulse time (in microseconds)
    max_pulse = CInt(2400)

    def _min_pulse_changed(self):
        if self.traits_inited():
            self.setup()

    def _max_pulse_changed(self):
        if self.traits_inited():
            self.setup()

    def setup(self, *args, **kwargs):
        super(ArduinoServoActuator, self).setup(*args, **kwargs)
        self.logger.debug("setup_servo %s %s %s %s %s %s", self, self.dev, self.pin, self.min_pulse, self.max_pulse,
                          int(round(self._status)))
        self._arduino.setup_servo(self.dev, self.pin, self.min_pulse, self.max_pulse, int(round(self._status)))

    def _status_changed(self):
        self.logger.debug("change_servo %s %s %s", self.dev, self.pin, int(round(self._status)))
        self._arduino.change_digital(self.dev, self.pin, int(round(self._status)))

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.dev, self.pin)

class ArduinoPWMActuator(FloatActuator, AbstractArduinoActuator):

    """
        Float-valued actuator object for Arduino output pins that can be configured in PWM mode
        Status is float between 0.0 and 1.0.
    """

    def setup(self, *args, **kwargs):
        super(ArduinoPWMActuator, self).setup(*args, **kwargs)
        self._arduino.setup_pwm(self.dev, self.pin)

    def _status_changed(self):
        self._arduino.change_digital(self.dev, self.pin, max(0., min(1., self._status)))

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.dev, self.pin)