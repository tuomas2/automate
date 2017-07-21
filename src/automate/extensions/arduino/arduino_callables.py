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
    # TODO docstrings
    _arduino = Any(transient=True)

    def setup_callable_system(self, system, init=False):
        rv = super(VirtualWireCommand, self).setup_callable_system(system, init=init)
        self._arduino = self.system.request_service('ArduinoService')
        return rv

    def call(self, caller, **kwargs):
        if not caller:
            return
        args = [self.call_eval(i, caller, **kwargs) for i in self._args]

        return self._arduino.send_virtualwire_command(*args)


class VirtualWireMessage(AbstractCallable):
    _arduino = Any(transient=True)

    def setup_callable_system(self, system, init=False):
        rv = super(VirtualWireMessage, self).setup_callable_system(system, init=init)
        self._arduino = self.system.request_service('ArduinoService')
        return rv

    def call(self, caller, **kwargs):
        if not caller:
            return
        args = [self.call_eval(i, caller, **kwargs) for i in self._args]

        return self._arduino.send_virtualwire_message(*args)

