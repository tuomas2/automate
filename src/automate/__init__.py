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

from __future__ import absolute_import
from __future__ import unicode_literals

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("automate").version
except pkg_resources.DistributionNotFound:
    __version__ = 'not installed'

from . import traits_fixes
from .common import *
from .program import *
from .system import *
from .callables import *
from .actuators import *
from .sensors import *
from .services import *
from .tools import *
from .statusobject import *
