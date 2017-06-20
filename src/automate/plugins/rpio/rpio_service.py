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

from threading import Thread

from traits.api import CBool, Any
from automate.service import AbstractSystemService
import signal


class RpioService(AbstractSystemService):

    """
        Service that provides interface to Raspberry Pi GPIO via
        `RPIO library <http://pythonhosted.org/RPIO/>`_.
    """

    #: Perform GPIO cleanup when exiting (default: False).
    gpio_cleanup = CBool(False)

    _gpio_thread = Any

    _RPIO = Any

    def setup(self):
        self.logger.info("Initializing RpioService (Raspberry Pi GPIO support)")
        try:
            import RPIO
            import RPIO.PWM
        except (ImportError, SystemError):
            self.logger.warning('RPIO module could not be imported. Enabling mocked RPIO')
            self.logger.warning("To use Raspberry Pi GPIO ports (sensors / actuators) please install module RPIO")
            import mock
            RPIO = mock.MagicMock()

        self._RPIO = RPIO

        self._RPIO.setmode(RPIO.BCM)
        self._gpio_thread = t = Thread(target=RPIO.wait_for_interrupts, name='RpioService thread')
        t.daemon = True
        t.start()

        self.logger.info("RPIO initialized")

    def cleanup(self):
        self._RPIO.stop_waiting_for_interrupts()
        self._RPIO.cleanup_interrupts()
        self._gpio_thread.join()
        if self.gpio_cleanup:
            self._RPIO.cleanup()

    def enable_input_port(self, port, callback, pull_up_down):
        self._RPIO.setup(port, self._RPIO.IN)
        pud = {"down": self._RPIO.PUD_DOWN, "up": self._RPIO.PUD_UP, "none": self._RPIO.PUD_OFF}
        self._RPIO.add_interrupt_callback(port, callback, edge="both", pull_up_down=pud[pull_up_down])

    def get_input_status(self, port):
        return self._RPIO.input(port)

    def disable_input_port(self, port):
        self._RPIO.del_interrupt_callback(port)

    def enable_output_port(self, port):
        self._RPIO.setup(port, self._RPIO.OUT)

    def disable_output_port(self, port):
        self._RPIO.setup(port, self._RPIO.IN)

    def get_pwm_module(self):
        try:
            self._RPIO.PWM.setup()
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
            self.logger.warning('SIGCHLD is now ignored totally due to RPIO.PWM bug. Might cause side effects!')
        except RuntimeError as e:
            if 'has already been called before' in e.message:
                pass
            else:
                raise e

        return self._RPIO.PWM

    def set_output_port_status(self, port, status):
        self._RPIO.output(port, status)
