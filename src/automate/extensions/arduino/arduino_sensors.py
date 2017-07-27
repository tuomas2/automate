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
from traits.api import CInt, Instance, CFloat, CBool, CStr, Int, Any, Enum
import pyfirmata

from automate.service import AbstractSystemService
from automate.statusobject import AbstractSensor
from . import arduino_service

class AbstractArduinoSensor(AbstractSensor):
    """
        Abstract base class for Arduino sensors
    """

    user_editable = CBool(False)

    #: Arduino service number (specify, if more than 1 ArduinoServices are configured in system)
    service = CInt(0)

    #: Arduino pin number
    pin = CInt

    _arduino = Instance(AbstractSystemService, transient=True)

    def setup(self, *args, **kwargs):
        super(AbstractArduinoSensor, self).setup(*args, **kwargs)
        self._arduino = self.system.request_service('ArduinoService', self.service)


class ArduinoDigitalSensor(AbstractArduinoSensor):
    """
        Boolean-valued sensor object for digital Arduino input pins
    """

    _status = CBool

    #: Enable built-in pull-up resistor
    pull_up_resistor = CBool(False)

    def setup(self, *args, **kwargs):
        super(ArduinoDigitalSensor, self).setup(*args, **kwargs)
        self._arduino.subscribe_digital(self.pin, self)
        if self.pull_up_resistor:
            self._arduino.set_pin_mode(self.pin, arduino_service.PIN_MODE_PULLUP)

    def cleanup(self):
        self._arduino.unsubscribe_digital(self.pin)


class ArduinoAnalogSensor(AbstractArduinoSensor):

    """
        Float-valued sensor object for analog Arduino input pins
    """
    _status = CFloat

    def setup(self, *args, **kwargs):
        super(ArduinoAnalogSensor, self).setup(*args, **kwargs)
        self._arduino.subscribe_analog(self.pin, self)

    def cleanup(self):
        self._arduino.unsubscribe_analog(self.pin)


class ArduinoRemoteDigitalSensor(AbstractArduinoSensor):

    """
        Sensor which listens to status changes of remote digital input pin
        (transmission via VirtualWire).

        Needs `AutomateFirmata <https://github.com/tuomas2/AutomateFirmata>`_
    """

    _status = CBool

    #: Source device number
    device = CInt

    def setup(self, *args, **kwargs):
        super(ArduinoRemoteDigitalSensor, self).setup(*args, **kwargs)
        self._arduino.subscribe_virtualwire_digital_broadcast(self, self.device)
        self._arduino.send_virtualwire_command(self.device,
                                               arduino_service.VIRTUALWIRE_SET_PIN_MODE,
                                               self.pin,
                                               pyfirmata.INPUT)

    def cleanup(self):
        self._arduino.unsubscribe_virtualwire_digital_broadcast(self, self.device)


class ArduinoRemoteAnalogSensor(AbstractArduinoSensor):

    """
        Sensor which listens to status changes of remote analog input pin
        (transmission via VirtualWire)

        Needs `AutomateFirmata <https://github.com/tuomas2/AutomateFirmata>`_
    """

    _status = CFloat

    #: Source device number
    device = CInt

    def setup(self, *args, **kwargs):
        super(ArduinoRemoteAnalogSensor, self).setup(*args, **kwargs)
        self._arduino.subscribe_virtualwire_analog_broadcast(self, self.device)

    def cleanup(self):
        self._arduino.unsubscribe_virtualwire_analog_broadcast(self, self.device)


