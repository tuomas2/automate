# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of automate-rpio.
#
# automate-rpio is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# automate-rpio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with automate-rpio.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
from __future__ import unicode_literals
from traits.api import Instance, Int, Bool, Enum, CUnicode, CFloat, CBool
from automate.sensors import UserBoolSensor, AbstractPollingSensor, UserFloatSensor
from automate.service import AbstractSystemService


class RpioSensor(UserBoolSensor):

    """
        Boolean-valued sensor object that reads Raspberry Pi GPIO input pins.
    """

    user_editable = CBool(False)

    #: GPIO port
    port = Int

    #: Set to True to have inversed status value
    inverted = Bool(False)

    #: Button setup: "down": pushdown resistor, "up": pushup resistor, or "none": no resistor set up.
    button_type = Enum("down", "up", "none")

    view = UserBoolSensor.view + ["port", "button_type"]

    _hw_service = Instance(AbstractSystemService, transient=True)

    def setup(self):
        self._hw_service = self.system.request_service('RpioService')

        self._hw_service.enable_input_port(self.port, self.gpio_callback, self.button_type)

    def _button_type_changed(self, new):
        if self._hw_service:
            self._hw_service.disable_input_port(self.port)
            self._hw_service.enable_input_port(self.port, self.gpio_callback, new)

    def gpio_callback(self, gpio_id, value):
        self.set_status(value if not self.inverted else not value)

    def update_status(self):
        self.gpio_callback(None, self._hw_service.get_input_status(self.port))

    def _port_changed(self, old, new):
        if not self._hw_service:
            return
        if old:
            self._hw_service.disable_input_port(old)
        self._hw_service.enable_input_port(new, self.gpio_callback, self.button_type)


class TemperatureSensor(AbstractPollingSensor):

    """
        W1 interface (on Raspberry Pi board) that polls polling temperature.
        (kernel modules w1-gpio and w1-therm required).
        Not using RPIO, but placed this here, since this is also Raspberry Pi related sensor.
    """

    _status = CFloat

    #: Address of W1 temperature sensor (something like ``"28-00000558263c"``), see what you have in
    #: ``/sys/bus/w1/devices/``
    addr = CUnicode
    view = list(set(UserFloatSensor.view + AbstractPollingSensor.view + ["addr"]))

    #: Maximum jump in temperature, between measurements. These temperature sensors
    #: tend to give sometimes erroneous results.
    max_jump = CFloat(5.0)

    _error_count = Int(0, transient=True)

    #: Maximum number of erroneous measurements, until value is really set
    max_errors = Int(5)

    _first_reading = CBool(True, transient=True)

    def get_status_display(self, **kwargs):
        if 'value' in kwargs:
            value = kwargs['value']
        else:
            value = self.status
        return u"%.1f ⁰C" % value

    def update_status(self):
        w1file = "/sys/bus/w1/devices/%s/w1_slave" % self.addr
        try:
            f = open(w1file)
        except IOError:
            return

        try:
            temp = float(f.read().split("\n")[1].split(" ")[9].split("=")[1]) / 1000.
        except IOError:
            self.logger.error("IO-error in temperature sensor %s, not set", self.name)
            return
        if abs(temp-self.status) > self.max_jump and self._error_count < self.max_errors and not self._first_reading:
            self._error_count += 1
        else:
            self._first_reading = False
            self._error_count = 0
            self.set_status(temp)
        f.close()
