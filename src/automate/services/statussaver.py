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

from __future__ import unicode_literals
from threading import Timer

from traits.api import Unicode, Any, CBool, CFloat

from automate.service import AbstractUserService

__all__ = ['StatusSaverService']


class StatusSaverService(AbstractUserService):

    """
        Service which is responsible for scheduling dumping system into file periodically.
    """

    autoload = True

    #: Dump saving interval, in seconds. Default 30 minutes.
    dump_interval = CFloat(30 * 60)

    _exit = CBool(False)
    _timer = Any(transient=True)

    def setup(self):
        if self.system.filename:
            self.system.on_trait_change(self.exit_save, "pre_exit_trigger")
            if self.dump_interval:
                self.save_system_periodically()

    def save_system_periodically(self):
        self.logger.debug('Saving system state')
        self.system.save_state()
        self._timer = Timer(self.dump_interval, self.save_system_periodically)
        self._timer.start()

    def exit_save(self):
        self.system.save_state()
        self._exit = True

    def cleanup(self):
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
