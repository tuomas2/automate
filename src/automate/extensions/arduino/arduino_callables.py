# (c) 2015-2017 Tuomas Airaksinen
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
from traits.trait_types import Any

from automate import AbstractCallable


class VirtualWireCommand(AbstractCallable):
    """
        Send VirtualWire command. Positional Arguments::

          - Recipient device number
          - VirtualWire command byte (see arduino_service.VIRTUALWIRE_*)
          - Command arguments...

        Keyword arguments:

          - service: Arduino service number (defaults to 0)

    """

    def call(self, caller, **kwargs):
        if not caller:
            return

        args = [self.call_eval(i, caller, **kwargs) for i in self._args]
        _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
        service = _kwargs.pop('service', 0)
        arduino = self.system.request_service('ArduinoService', service)

        return arduino.send_virtualwire_command(*args)


class LCDSetBacklight(AbstractCallable):
    """
        Set LCD backlight on/off. Positional Arguments::

          - LCD on/off value

        Keyword arguments:

          - service: Arduino service number (defaults to 0)
    """

    def call(self, caller, **kwargs):
        if not caller:
            return

        args = [self.call_eval(i, caller, **kwargs) for i in self._args]
        _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
        service = _kwargs.pop('service', 0)
        arduino = self.system.request_service('ArduinoService', service)

        return arduino.lcd_set_backlight(bool(args[0]))


class LCDPrint(AbstractCallable):
    """
        Print string to LCD. Positional Arguments::

          - Value to be printed on LCD

        Keyword arguments:

          - service: Arduino service number (defaults to 0)
    """

    def call(self, caller, **kwargs):
        if not caller:
            return

        args = [self.call_eval(i, caller, **kwargs) for i in self._args]
        _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
        service = _kwargs.pop('service', 0)
        arduino = self.system.request_service('ArduinoService', service)

        return arduino.lcd_print(str(args[0]))


class FirmataCommand(AbstractCallable):
    """
    Send custom Firmata command to Arduino. Positional arguments::

     - Firmata command byte
     - Arguments...

    Keyword arguments::

     - service: Arduino service number (defaults to 0)
    """
    def call(self, caller, **kwargs):
        if not caller:
            return
        args = [self.call_eval(i, caller, **kwargs) for i in self._args]
        _kwargs = {k: self.call_eval(v, caller, **kwargs) for k, v in list(self._kwargs.items())}
        service = _kwargs.pop('service', 0)
        arduino = self.system.request_service('ArduinoService', service)
        arduino.write(*args)

