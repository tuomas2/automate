from __future__ import unicode_literals
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

from automate import *
import pytest, mock
from datetime import datetime


def unix_time(dt):
    epoch = datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return delta.total_seconds()


@pytest.mark.parametrize('_timer_on, _timer_off, now, status', [
    ('0 10 * * *', '0 11 * * *', datetime(2015, 1, 1, 10, 30), True),
    ('0 10 * * *', '0 11 * * *', datetime(2015, 1, 1, 11, 30), False),
    ('0 10 * * *', '0 11 * * *', datetime(2015, 1, 1, 9, 30), False),
    ('0 10 * * *;0 12 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 10, 30), True),
    ('0 10 * * *;0 12 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 11, 30), False),
    ('0 10 * * *;0 12 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 12, 30), True),
    ('0 10 * * *;0 12 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 10, 00), True),
    ('0 10 * * *;0 12 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 11, 00), False),
    ('0 10 * * *;0 12 * * *;0 15 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 15, 00), True),
    ('0 10 * * *;0 12 * * *;0 15 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 9, 30), True),
    ('0 10 * * *;0 12 * * *;0 15 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 10, 30), True),
    ('0 10 * * *;0 12 * * *;0 15 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 11, 00), False),
    ('0 10 * * *;0 12 * * *;0 15 * * *', '0 11 * * *; 0 13 * * *', datetime(2015, 1, 1, 13, 00), False),
])
def test_crontimersensor(_timer_on, _timer_off, now, status, sysloader):
    with mock.patch('automate.CronTimerSensor._now', lambda self: now):
        class ms(System):
            t = CronTimerSensor(timer_on=_timer_on, timer_off=_timer_off)

        s = sysloader.new_system(ms)
        assert s.t.status == status
