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
import logging.handlers

from traits.api import Any, Int, Str, Unicode
from colorlog import ColoredFormatter
import ansiconv

from automate.service import AbstractUserService

__all__ = ['LogStoreService']


class LogStoreService(AbstractUserService):

    """
        Provides interface to log output. Used by WebService.
    """
    autoload = True

    #: Log level
    log_level = Int(logging.INFO)

    #: Log length
    log_length = Int(100)

    #: The most recent log line is always updated here.
    #:t Subscription to this attribute can be used to follow new log entries.
    most_recent_line = Unicode

    format = Str('%(log_color)s%(asctime)s %(name)s %(message)s %(reset)s')
    html_format = Str('%(white)s%(asctime)s %(log_color)s%(name)s%(white)s %(message)s %(reset)s')
    time_format = Str('%H:%M:%S')

    _loghandler = Any

    def _log_level_changed(self, new):
        self._loghandler.setLevel(new)

    @staticmethod
    def html_fix(s):
        return s.replace('<', '&lt;').replace('>', '&gt;')


    def setup(service):
        html_formatter = ColoredFormatter(service.html_format, datefmt='%H:%M:%S')

        class MyBufferingHandler(logging.handlers.BufferingHandler):

            def flush(self):
                del self.buffer[:int(.25 * self.capacity)]

            def emit(self, record):
                super(MyBufferingHandler, self).emit(record)
                service.most_recent_line = ansiconv.to_html(service.html_fix(html_formatter.format(record))) + '\n'

        service._loghandler = loghandler = MyBufferingHandler(service.log_length)
        loghandler.setLevel(service.log_level)
        loghandler.setFormatter(ColoredFormatter(service.format, datefmt=service.time_format))
        service.system.logger.addHandler(loghandler)

    def lastlog(self, lines=20, format='', html=True):
        handler = self._loghandler
        if format:
            formatter = ColoredFormatter(format, datefmt=self.time_format)
        else:
            formatter = ColoredFormatter(self.html_format if html else self.format, datefmt=self.time_format)

        rv = u'\n'.join([formatter.format(i) for i in handler.buffer[-lines:]])

        if html:
            rv = ansiconv.to_html(self.html_fix(rv))
        else:
            rv = ansiconv.to_plain(rv)
        return rv

    def cleanup(self):
        return
