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
from pytest import approx
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


def test_history(sysloader):
    class HistoryTest(System):
        s = UserBoolSensor(history_length=5, default=False)

    sys = sysloader.new_system(HistoryTest)

    assert len(sys.s.history) == 0
    sys.s.status=True
    sys.flush()
    assert len(sys.s.history) == 1
    sys.s.status=True
    sys.flush()
    assert len(sys.s.history) == 1
    sys.s.status=False
    sys.flush()
    assert len(sys.s.history) == 2


def test_history_math(sysloader):
    class HistoryTest(System):
        s = UserFloatSensor(history_length=20, default=0)
    sys = sysloader.new_system(HistoryTest)

    s = sys.s
    s.history = [(0, 0.), (1, 1.), (2, 0.5)]
    assert s.status_at_time(0) == approx(0.)
    assert s.status_at_time(0.5) == approx(0.)
    assert s.status_at_time(1) == approx(1.)
    with pytest.raises(ValueError):
        assert s.status_at_time(-0.5) == approx(1.)

    assert s.status_at_time(2) == approx(0.5)
    assert s.status_at_time(3) == approx(0.5)

    with pytest.raises(ValueError):
        assert s.integral(-1,1) == approx(0)

    assert s.integral(0,1) == approx(0)
    assert s.integral(1,2) == approx(1)

    assert s.integral(0.1,1) == approx(0)
    assert s.integral(0.1,1.5) == approx(0.5)

    assert s.integral(1.1,2) == approx(0.9)
    assert s.integral(1.1,1.9) == approx(0.8)

    assert s.integral(0,2) == approx(1)
    assert s.integral(2,3) == approx(0.5)
    assert s.integral(2,4) == approx(1.0)
    assert s.integral(0,3) == approx(1.5)
    assert s.integral(0,4) == approx(2)


def test_history_integral(sysloader):
    class HistoryTest(System):
        s = UserFloatSensor(history_length=20, default=0)
        trig = UserBoolSensor(
            triggers=['trig'],
            on_update=SetStatus('s2', Integral('s', 0, 3))
        )

        s2 = FloatActuator()
    sys = sysloader.new_system(HistoryTest)

    s = sys.s
    s2 = sys.s2
    assert s2.status == approx(0.)
    s.history = [(0, 0.), (1, 1.), (2, 0.5)]
    assert s.integral(0,3) == approx(1.5)

    sys.trig.status = 1
    sys.flush()
    assert s2.status == approx(1.5)




def test_full_integral(sysloader):
    class HistoryTest(System):
        s = UserFloatSensor(history_length=20, default=0)
        trig = UserBoolSensor(
            triggers=['trig'],
            on_update=SetStatus('s2', Integral('s'))
        )

        s2 = FloatActuator()
    sys = sysloader.new_system(HistoryTest)

    s = sys.s
    s2 = sys.s2
    assert s2.status == approx(0.)
    s.history = [(0, 0.), (1, 1.), (2, 0.5)]
    with mock.patch("time.time", new_callable=lambda *args: lambda *args: 2):
        assert s.full_integral == approx(1)

        sys.trig.status = 1
        sys.flush()
        assert s2.status == approx(1)
