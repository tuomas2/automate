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

from __future__ import unicode_literals
from traits.api import CInt, CBool, Instance, Any, CFloat, Property
from automate.service import AbstractSystemService
from automate.statusobject import AbstractActuator


class RpioActuator(AbstractActuator):

    """
        Boolean-valued actuator for setting Raspberry Pi GPIO port statuses (on/off).
    """

    _status = CBool(transient=True)

    #: GPIO port id
    port = CInt

    #: Set to True to have inversed status value
    inverted = CBool(False)

    _rpio = Instance(AbstractSystemService, transient=True)

    view = AbstractActuator.view + ["port"]

    def setup(self):
        self._rpio = self.system.request_service('RpioService')
        self._rpio.enable_output_port(self.port)

    def _port_changed(self, old, new):
        if not self._rpio:
            return
        if old:
            self._rpio.disable_output_port(old)

        self._rpio.enable_output_port(new)

    def _status_changed(self):
        self.logger.debug("%s gpio actuator status changed %s", self.name, repr(self._status))
        self._rpio.set_output_port_status(self.port, self._status if not self.inverted else not self._status)


class RpioPWMActuator(AbstractActuator):

    """
        Actuator to control PWM (pulse-width-modulation) ports on Raspberry pi GPIO.

        Status range 0...1

        This is not recommended to be used because RPIO PWM implementation is not very well behaving.
        I recommend to use ArduinoPWMActuator with an Arduino loaded with StandardFirmata. It's much more
        stable and robust solution.
    """

    _status = CFloat(transient=True)

    #: GPIO port number
    port = CInt

    #: RPIO PWM DMA channel
    dma_channel = CInt(0)

    #: PWM frequency (Hz)
    frequency = CFloat(50.)

    _subcycle = Property(trait=CInt, transient=True)

    view = AbstractActuator.view + ["port"]

    _pwm = Any(transient=True)

    _rpio = Instance(AbstractSystemService, transient=True)

    def _get__subcycle(self):
        return int(1. / self.frequency * 1e6)

    def setup(self):
        self._rpio = self.system.request_service('RpioService')
        self._pwm = self._rpio.get_pwm_module()
        self._port_changed(None, self.port)

    def _port_changed(self, old, new):
        if not self._rpio:
            return

        if old:
            self._pwm.clear_channel_gpio(self.dma_channel, old)

        self._pwm.init_channel(self.dma_channel, self._subcycle)
        new = min(0.999, max(0., self._status))
        self._pwm.add_channel_pulse(self.dma_channel, self.port, 0, int(round(new * self._subcycle / 10.)))

    def _frequency_changed(self):
        self._port_changed(self.port, self.port)

    def _status_changed(self):
        self.logger.debug("PWMActuator %s change %s", self, self._status)

        PWM = self._pwm

        PWM.clear_channel_gpio(self.dma_channel, self.port)
        new = min(0.999, max(0., self._status))
        PWM.add_channel_pulse(self.dma_channel, self.port, 0, int(round(new * self._subcycle / 10.)))
