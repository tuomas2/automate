from __future__ import unicode_literals
from builtins import range
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

from collections import deque

import pytest
import time

from automate import *
from automate import Group
from automate.program import Program

logger = logging.getLogger('automate.tests')

DELAYTIME = 1.0
SLEEPTIME = 1.7 * DELAYTIME
LOW = 1.0
HIGH = 100.0
AMOUNT = 20


@pytest.yield_fixture(params=[0, 1, 2])
def mysys_old(request):
    if request.param == 0:
        class _mysys(System):
            act = FloatActuator(default=LOW, debug=True)
            slaveact = FloatActuator(default=LOW, debug=True, slave=True)
            slavebinact = BoolActuator(default=False, debug=True, slave=True)
            sens = UserBoolSensor(default=False, debug=True)
            s1 = UserBoolSensor(default=False, debug=True)
            s2 = UserFloatSensor(default=HIGH)
            slaveprog = Program(active_condition=Value(s1),
                                on_update=SetStatus(slaveact, s2))
            p2 = Program(active_condition=Value(s1),
                         on_activate=SetStatus(act, HIGH),
                         priority=2,
                         )
            prog = Program(
                active_condition=Value(sens),
                on_activate=SetStatus(act, HIGH),
            )
    elif request.param == 1:
        class _mysys(System):
            act = FloatActuator(default=LOW, debug=True)
            slaveact = FloatActuator(default=LOW, debug=True, slave=True)
            slavebinact = BoolActuator(default=False, debug=True, slave=True)
            sens = UserBoolSensor(default=False, debug=True)
            s1 = UserBoolSensor(default=False, debug=True)
            s2 = UserFloatSensor(default=HIGH)

            slaveprog = Program(active_condition=Value('s1'),
                                on_update=SetStatus('slaveact', 's2'))
            p2 = Program(active_condition=Value('s1'),
                         on_activate=SetStatus('act', HIGH),
                         priority=2,
                         )
            prog = Program(
                active_condition=Value('sens'),
                on_activate=SetStatus('act', HIGH),
            )
    else:
        class _mysys(System):

            class group1(Group):
                act = FloatActuator(default=LOW, debug=True)
                slaveact = FloatActuator(default=LOW, debug=True, slave=True)
                slavebinact = BoolActuator(default=False, debug=True, slave=True)
                sens = UserBoolSensor(default=False, debug=True)

                class group3(Group):
                    s1 = UserBoolSensor(default=False, debug=True)
                    s2 = UserFloatSensor(default=HIGH)

            class group2(Group):
                slaveprog = Program(active_condition=Value('s1'),
                                    on_update=SetStatus('slaveact', 's2'))
                p2 = Program(active_condition=Value('s1'),
                             on_activate=SetStatus('act', HIGH),
                             priority=2,
                             )
                prog = Program(
                    active_condition=Value('sens'),
                    on_activate=SetStatus('act', HIGH),
                )

    yield _mysys
#    s = _mysys(exclude_services=['TextUiService'])
#    s.namespace['defprog'] = s.act.program
#    s.flush()
#    s.logger.info('UNITTEST %s', request)
#    yield s
#    s.cleanup()


@pytest.yield_fixture
def mysys(mysys_old, sysloader):
    s = sysloader.new_system(mysys_old)
    s.namespace['defprog'] = s.act.program
    yield s

#@pytest.yield_fixture
# def mysys(mysys_old):
#    s = mysys_old(exclude_services=['TextUiService'])
#    s.namespace['defprog'] = s.act.program
#    yield s
#    s.cleanup()


@pytest.yield_fixture
def mysys_groups():
    class _mysys(System):

        class group1(Group):
            s1 = UserFloatSensor(default=HIGH)

        class group2(Group):
            s2 = UserFloatSensor(default=HIGH)

            class group3(Group):
                s3 = UserFloatSensor()

        act = FloatActuator(default=LOW, debug=True)
        p2 = Program(active_condition=Value('s1'),
                     on_activate=SetStatus('act', HIGH),
                     priority=2,
                     )

    s = _mysys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()


def test_groups(mysys_groups):
    s = mysys_groups
    assert {'group:group1'} == s.s1.tags
    assert {'group:group2'} == s.s2.tags
    assert s.s3.tags == {'group:group2', 'group:group3'}  # 'group:group2.group3'}
    assert s.p2.active_condition.obj is s.s1
    assert s.p2.on_activate.obj is s.act
    assert s.p2.on_activate.value is HIGH


def test_samename(caplog):
    class _mysys(System):

        class group1(Group):
            s1 = UserFloatSensor(default=HIGH)

        class group2(Group):
            s1 = UserFloatSensor(default=HIGH)
    with pytest.raises(NameError):
        s = _mysys()
    caplog.error_ok = True


def test_slave_actuator(mysys):

    with pytest.raises(ValueError):
        mysys.act.status = HIGH

    assert mysys.act._status == LOW
    a = mysys.slaveact
    assert a._status == LOW
    a.status = HIGH
    mysys.flush()
    assert a._status == HIGH
    a.set_status(LOW)
    mysys.flush()
    assert a._status == LOW
    mysys.s1.set_status(True)
    mysys.flush()
    assert a._status == HIGH
    mysys.s2.set_status(LOW)  # slaveprog should set status of a to LOW
    mysys.flush()
    assert a._status == LOW
    assert mysys.slaveprog.active
    assert a in mysys.slaveprog.actual_targets
    mysys.s1.set_status(False)
    mysys.flush()
    assert not mysys.slaveprog.active
    # if program is deactivated, slave actuator status is not changed
    # I'm not sure if it should be changed back to default value, but
    # not it's like that
    assert a._status == LOW


def test_default_statuses(mysys):
    assert mysys.sens._status == False
    assert mysys.s1._status == False
    assert mysys.act._status == LOW
    assert mysys.slaveact._status == LOW


def test_program_activation(mysys):
    assert mysys.act.program == mysys.defprog
    assert len(mysys.act.program_stack) == 1
    assert mysys.act.status == LOW
    assert mysys.act.get_program_status(mysys.prog) == None
    assert mysys.prog.active == False
    assert mysys.act.program.name == 'dp_act'
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.program == mysys.prog
    assert mysys.act.program_status == {mysys.defprog: LOW, mysys.prog: HIGH}
    assert len(mysys.act.program_stack) == 2

    assert mysys.sens.status == True
    assert mysys.act.get_program_status(mysys.prog) == HIGH
    assert mysys.prog.active == True
    assert mysys.act.status == HIGH
    assert mysys.act.program.name == 'prog'

    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.program.name == 'dp_act'
    assert mysys.act.program == mysys.defprog
    assert len(mysys.act.program_stack) == 1
    assert mysys.act.program_status == {mysys.defprog: LOW}


def test_back_and_forth_on_activate(mysys):
    assert mysys.act.status == LOW
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == LOW
    logger.debug('STARTING')
    for i in range(AMOUNT):
        mysys.sens.set_status(True)
        mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.sens.status == False
    assert mysys.act.status == LOW


def test_back_and_forth_on_activate_w_safety_delay(mysys):
    mysys.act.safety_delay = 5*DELAYTIME
    mysys.act.debug = True
    assert mysys.act.status == LOW
    mysys.sens.set_status(True)
    mysys.sens.set_status(False)
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == LOW
    mysys.act._last_changed = time.time()
    for i in range(AMOUNT):
        mysys.sens.set_status(True)
        mysys.sens.set_status(False)
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.worker_thread.queue.queue == deque([])
    assert mysys.worker_thread.queue.unfinished_tasks == 0
    assert mysys.act.status == LOW


def test_back_and_forth_on_update(mysys):
    assert mysys.act.status == LOW
    mysys.prog.active_condition = Value(True)
    mysys.prog.update_condition = Value(True)
    mysys.prog.on_update = SetStatus(mysys.act, mysys.sens)
    mysys.sens.set_status(True)
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == 0.0

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == 1.0
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == 0.0
    # what about if we quickly turn true&false?
    import random
    for i in range(AMOUNT):
        mysys.sens.set_status(True)
        # print i, mysys.worker_thread.queue.queue
        if random.random() < 0.01:
            time.sleep(0.01)
        mysys.sens.set_status(False)
        # print i, mysys.worker_thread.queue.queue
        # if random.random() < 0.02:
        #    time.sleep(0.01)
    mysys.flush()
    assert mysys.act.status == 0.0
    #assert False


def test_change_delay_with_two_progs(mysys):
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == HIGH
    mysys.act.change_delay = DELAYTIME
    mysys.act.change_mode = 'both'
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == HIGH
    assert mysys.act.changing
    mysys.s1.set_status(True)
    mysys.flush()
    assert mysys.act.status == HIGH
    assert not mysys.act.changing
    mysys.act._last_changed = time.time()
    time.sleep(SLEEPTIME)
    assert mysys.act.status == HIGH
    assert not mysys.act.changing


def test_change_delay_rising(mysys):
    assert mysys.act.safety_mode == 'rising'
    mysys.act.change_delay = DELAYTIME
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == LOW
    assert mysys.act.changing == True
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH
    mysys.act._last_changed = time.time()
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == LOW


def test_change_delay_both(mysys):
    mysys.act.change_delay = DELAYTIME
    mysys.act.change_mode = 'both'
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == LOW
    assert mysys.act.changing == True
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH
    mysys.act._last_changed = time.time()
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == HIGH
    assert mysys.act.changing == True
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == LOW


def test_change_delay_rising(mysys):
    mysys.act.change_delay = DELAYTIME
    mysys.act.change_mode = 'falling'
    mysys.act._last_changed = time.time()
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.status == HIGH
    assert mysys.act.changing == True
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == LOW


def test_change_delay_falling_issue23(mysys):
    mysys.act.change_delay = DELAYTIME  # = 3
    mysys.act.change_mode = 'falling'
    mysys.act._last_changed = time.time()
    mysys.sens.set_status(True)  # rising
    mysys.flush()
    mysys.sens.set_status(False)
    mysys.flush()
    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.status == HIGH
    time.sleep(0.9 * DELAYTIME)
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    time.sleep(0.9 * DELAYTIME)
    assert mysys.act.status == HIGH
    time.sleep(0.2 * DELAYTIME)  # must wait full change_delay after set_status(False)!
    assert mysys.act.status == LOW


def test_change_delay_falling_issue23_2(mysys):
    mysys.act.change_delay = DELAYTIME  # = 3
    mysys.act.change_mode = 'falling'
    mysys.act._last_changed = time.time()
    mysys.sens.set_status(True)  # rising
    mysys.flush()
    mysys.sens.set_status(False)
    mysys.flush()
    mysys.sens.set_status(True)
    mysys.flush()
    mysys.sens.set_status(False)
    assert mysys.act.status == HIGH
    time.sleep(0.9 * DELAYTIME)
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    mysys.flush()
    time.sleep(0.3 * DELAYTIME)
    assert mysys.act.status == LOW


def test_safety_delay_with_safety_mode_rising(mysys):
    mysys.act.safety_delay = DELAYTIME
    mysys.act._last_changed = 0.
    assert mysys.act.safety_mode == 'rising'
    assert mysys.sens.status == False
    assert mysys.sens.change_delay == 0.0

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.changing == False
    assert mysys.act.status == LOW

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.changing == True
    assert mysys.act.status == LOW
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH

    # reason for these: this caused at one point hanging
    mysys.sens.set_status(False)
    mysys.sens.set_status(True)
    mysys.sens.set_status(False)
    mysys.sens.set_status(True)
    mysys.sens.set_status(False)
    mysys.sens.set_status(True)


def test_safety_delay_with_safety_mode_both(mysys):
    mysys.act.safety_delay = DELAYTIME
    mysys.act._last_changed = 0.
    mysys.act.safety_mode = 'both'
    assert mysys.sens.status == False
    assert mysys.sens.change_delay == 0.0

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH

    mysys.act._last_changed = time.time()
    # set time so that there will not accumulate time difference that might fail test sometimes

    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.changing == True
    assert mysys.act.status == HIGH
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == LOW

    mysys.act._last_changed = time.time()

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.sens._status == True
    assert mysys.act.status == LOW
    assert mysys.act.changing == True
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH


def test_safety_delay_with_safety_mode_falling(mysys):
    mysys.act.safety_delay = DELAYTIME
    mysys.act._last_changed = 0.
    mysys.act.safety_mode = 'falling'
    assert mysys.sens.status == False
    assert mysys.sens.change_delay == 0.0

    mysys.sens.set_status(True)
    # mysys.flush()
    # assert mysys.sens.changing  # could have changed already, in theory
    #assert mysys.sens._queued_job
    mysys.flush()
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH
    mysys.sens.set_status(False)
    mysys.flush()
    assert mysys.act.changing == True
    assert mysys.act.status == HIGH
    time.sleep(SLEEPTIME)
    assert mysys.act.changing == False
    assert mysys.act.status == LOW

    mysys.sens.set_status(True)
    mysys.flush()
    assert mysys.act.changing == False
    assert mysys.act.status == HIGH


def test_statuschange(mysys, caplog):
    for a in [mysys.s1, mysys.slavebinact]:
        a.change_delay = 5
        a.set_status(True)
        mysys.flush()
        assert a.changing
        mysys.flush()
        assert a._status == False
        assert a._timed_action
        assert not '%s:INFO:Cancelling previous safety/change_delay action. Now changing to False' % a.name in caplog.text()
        a.set_status(False)
        mysys.flush()
        assert not a.changing
        assert not a._timed_action
        assert '%s:INFO:Cancelling previous safety/change_delay action. Now changing to False' % a.name in caplog.text()
        assert a._status == False
        assert not a.changing
        assert not a._timed_action


def test_sensor_resetdelay(sysloader):
    class mysys(System):
        s = UserIntSensor(default=2, reset_delay=0.1)
    s = sysloader.new_system(mysys)
    s.s.status = 1
    s.flush()
    assert s.s.status == 1
    time.sleep(0.2)
    assert s.s.status == 2


class MySensor(AbstractSensor):
    setup_called = CBool(False)

    def setup(self):
        self.setup_called = True


class MyActuator(AbstractActuator):
    setup_called = CBool(False)

    def setup(self):
        self.setup_called = True


def test_statusobject_setup(sysloader):
    class newsys(System):
        a = MySensor()
        b = MyActuator()
    s = sysloader.new_system(newsys)
    assert s.a.setup_called
    assert s.b.setup_called


class TestActuator(FloatActuator):
    change_count = CInt(0)

    def _status_changed(self):
        self.change_count += 1


def test_customactuator_statuschange(sysloader):
    class sys(System):
        testact = TestActuator(default=0.0)
        sens = UserFloatSensor(default=0.0)
        prog = Program(on_update=SetStatus(testact, sens))
    s = sysloader.new_system(sys)
    assert s.testact.change_count == 0
    s.sens.status = 1.0
    s.flush()
    assert s.testact.change_count == 1
    s.sens.status = 1.0
    s.flush()
    assert s.testact.change_count == 1
    s.sens.status = 2.0
    s.flush()
    assert s.testact.change_count == 2
    s.sens.status = 1.0
    s.flush()
    assert s.testact.change_count == 3


def test_on_activate_bug(sysloader):
    called = []

    def func(caller):
        called.append(1)

    class sys(System):
        after_reset = Program(
            update_condition=Value(False),
            on_update=Func(func),
        )

    s = sysloader.new_system(sys)
    assert not called

from traits.api import Int


def test_set_status_wrong_type(sysloader, caplog):
    caplog.error_ok = True

    class mysens(AbstractSensor):
        _status = Int

    class sys(System):
        s = mysens(default=0)
    s = sysloader.new_system(sys)
    s.s.status = 1.1
    s.flush()
    assert s.s.status == 0
