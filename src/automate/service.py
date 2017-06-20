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
import logging

from traits.api import HasStrictTraits, Instance

from automate.common import SystemBase


class AbstractService(HasStrictTraits):

    """
        Base class for System and UserServices
    """

    #: If set to *True*, service is loaded automatically (if not explicitly prevented
    #: in :attr:`automate.system.System.exclude_services`). Overwrite this in subclasses,
    autoload = False
    system = Instance(SystemBase)
    logger = Instance(logging.Logger)

    def setup_system(self, system, name=None):
        self.system = system
        self.logger = self.system.logger.getChild(self.__class__.__name__)
        self.logger.info('Setup')
        self.system.register_service(self)
        self.setup()

    def cleanup_system(self):
        if self.system:
            self.logger.info('Cleaning up')
            self.cleanup()

    def setup(self):
        """
            Initialize service here. Define in subclasses.
        """

    def cleanup(self):
        """
            Cleanup actions must be performed here. This must be blocking until service is
            fully cleaned up.

            Define in subclasses.
        """

    def reload(self):
        self.cleanup()
        self.setup()
        self.logger.info('Reloading %s ready!', self)

    def __repr__(self):
        return '<' + self.__class__.__name__ + ' instance%s>' % ('' if self.system else ' not initialized')


class AbstractUserService(AbstractService):

    """Baseclass for UserServices. These are set up on startup. They provide usually user interaction services."""


class AbstractSystemService(AbstractService):

    """Baseclass for SystemServices. These are set up by when first requested by Sensor or other object."""

    autoload = True
