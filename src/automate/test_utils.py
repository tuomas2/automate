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

import logging
import contextlib
import py


class CaptureLogHandler(logging.StreamHandler):
    """A logging handler that stores log records and the log text."""

    def __init__(self, *args, **kwargs):
        """Creates a new log handler."""
        super(CaptureLogHandler, self).__init__(*args, **kwargs)
        self.reset()

    def reset(self):
        self.stream = py.io.TextIO()
        self.records = []

    def close(self):
        """Close this log handler and its underlying stream."""

        super(CaptureLogHandler, self).close()
        self.stream.close()

    def emit(self, record):
        """Keep the log records in a list in addition to the log text."""

        self.records.append(record)
        super(CaptureLogHandler, self).emit(record)

    def text(self):
        """Returns the log text."""

        return self.stream.getvalue()

    @contextlib.contextmanager
    def atLevel(self, level, logger=None):
        """Context manager that sets the level for capturing of logs.

        By default, the level is set on the handler used to capture
        logs. Specify a logger name to instead set the level of any
        logger.
        """

        obj = logger and logging.getLogger(logger) or self
        old_level = obj.level
        obj.setLevel(level)
        yield self
        obj.setLevel(old_level)
