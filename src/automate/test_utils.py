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
logger = logging.getLogger('automate')
import pytest
import logging

from automate.system import System


@pytest.yield_fixture(params=[1])
def sysloader(request, tmpdir):
    filename = str(tmpdir.join('savefile.dmp'))
    if request.param:
        class Loader(object):

            def new_system(self, sys, *args, **kwargs):
                kwargs.setdefault('exclude_services', ['TextUIService'])
                self.sys = sys(*args, **kwargs)
                self.sys.flush()
                return self.sys
    else:
        class Loader(object):

            def new_system(self, sys, *args, **kwargs):
                kwargs.setdefault('exclude_services', ['TextUIService'])
                sys1 = sys(*args, **kwargs)
                sys1.flush()
                sys1.filename = filename
                sys1.save_state()
                sys1.cleanup()

                self.sys = System.load_or_create(filename, exclude_services=['TextUIService'])
                self.sys.flush()
                return self.sys

    loader = Loader()
    yield loader
    loader.sys.cleanup()


@pytest.yield_fixture(autouse=True)
def check_log(request, caplog):
    formatter = logging.Formatter(fmt='%(threadName)s:%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    caplog.handler.setFormatter(formatter)

    logger.info('UNITTEST %s', request)
    yield None
    if not getattr(caplog, 'error_ok', False):
        for i in caplog.records():
            if i.levelno >= logging.ERROR:
                raise Exception('Error: %s' % i.getMessage())
