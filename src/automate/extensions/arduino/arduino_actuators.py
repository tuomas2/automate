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
from traits.api import CInt, Instance, CBool, CFloat, CStr

import pyfirmata

from automate.actuators import FloatActuator
from automate.service import AbstractSystemService
from automate.statusobject import AbstractActuator
from . import arduino_service


class AbstractArduinoActuator(AbstractActuator):
    """
        Abstract base class for Arduino actuators
    """

    #: Arduino service number (specify, if more than 1 ArduinoService are configured in the system)
    service = CInt(0)

    #: Arduino pin number
    pin = CInt

    _arduino = Instance(AbstractSystemService, transient=True)

    view = AbstractActuator.view + ["pin"]
    simple_view = AbstractActuator.simple_view + ["pin"]

    def setup(self, *args, **kwargs):
        super(AbstractArduinoActuator, self).setup(*args, **kwargs)
        self._arduino = self.system.request_service('ArduinoService', self.service)


class ArduinoDigitalActuator(AbstractArduinoActuator):
    """
        Boolean-valued actuator object for digital Arduino output pins
    """
    _status = CBool(transient=True)

    def setup(self, *args, **kwargs):
        super(ArduinoDigitalActuator, self).setup(*args, **kwargs)
        self._arduino.setup_digital(self.pin)

    def _status_changed(self):
        self._arduino.change_digital(self.pin, self._status)

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.pin)


class ArduinoRemoteDigitalActuator(AbstractArduinoActuator):
    """
        Actuator that sends target device digital output pin status change requests

        Needs `AutomateFirmata <https://github.com/tuomas2/AutomateFirmata>`_
    """

    _status = CBool(transient=True)

    #: Target device number
    device = CInt

    def setup(self, *args, **kwargs):
        super(ArduinoRemoteDigitalActuator, self).setup(*args, **kwargs)
        self._arduino.send_virtualwire_command(self.device,
                                               arduino_service.VIRTUALWIRE_SET_PIN_MODE,
                                               self.pin,
                                               pyfirmata.OUTPUT)

    def _status_changed(self):
        self._arduino.send_virtualwire_command(self.device,
                                               arduino_service.VIRTUALWIRE_SET_DIGITAL_PIN_VALUE,
                                               self.pin,
                                               self.status)


class ArduinoRemotePWMActuator(AbstractArduinoActuator):
    """
        Actuator that sends target device analog (PWM) output pin status change requests

        Needs `AutomateFirmata <https://github.com/tuomas2/AutomateFirmata>`_
    """

    _status = CFloat(transient=True)

    #: Target device number
    device = CInt

    def setup(self, *args, **kwargs):
        super(ArduinoRemotePWMActuator, self).setup(*args, **kwargs)
        self._arduino.send_virtualwire_command(self.device,
                                               arduino_service.VIRTUALWIRE_SET_PIN_MODE,
                                               self.pin,
                                               pyfirmata.PWM)

    def _status_changed(self):
        value = min(max(self.status, 0.), 1.)
        value = int(round(value * 255))  # Arduino PWM has 8 bit resolution
        self._arduino.send_virtualwire_command(self.device,
                                               arduino_service.VIRTUALWIRE_ANALOG_MESSAGE,
                                               self.pin,
                                               value)


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
        self.logger.debug("setup_servo %s %s %s %s %s %s", self, self.service, self.pin, self.min_pulse, self.max_pulse,
                          int(round(self._status)))
        self._arduino.setup_servo(self.pin, self.min_pulse, self.max_pulse, int(round(self._status)))

    def _status_changed(self):
        self.logger.debug("change_servo %s %s %s", self.pin, int(round(self._status)))
        self._arduino.change_digital(self.pin, int(round(self._status)))

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.pin)


class ArduinoPWMActuator(FloatActuator, AbstractArduinoActuator):

    """
        Float-valued actuator object for Arduino output pins that can be configured in PWM mode
        Status is float between 0.0 and 1.0.
    """

    def setup(self, *args, **kwargs):
        super(ArduinoPWMActuator, self).setup(*args, **kwargs)
        self._arduino.setup_pwm(self.pin)

    def _status_changed(self):
        self._arduino.change_digital(self.pin, max(0., min(1., self._status)))

    def cleanup(self):
        self._arduino.cleanup_digital_actuator(self.pin)