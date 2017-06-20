from __future__ import unicode_literals
from builtins import object
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

import pytest

from automate import *
from automate.program import Program


@pytest.fixture(params=[Program, UserBoolSensor, BoolActuator])
def progtype(request):
    return request.param


@pytest.yield_fixture(params=[0, 1])
def mysys(request, progtype):
    class sys(System):
        s1 = UserBoolSensor()
        s2 = UserBoolSensor()
        a1 = BoolActuator(default=False)
        a2 = BoolActuator()
        p = progtype()
        p1 = progtype(priority=1.0, active_condition=Value(True))
        p2 = progtype(priority=2.0, active_condition=Value(True))
        if request.param == 0:
            p3 = progtype(priority=2.0, active_condition=Value(False),
                          on_activate=Run(Run(SetStatus(a2, s1),)))
        else:
            p3 = progtype(priority=2.0, active_condition=Value(False),
                          on_activate=Run(Run(SetStatus('a2', 's1'))),
                          )
    s = sys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()


def test_correct_callable_setup(sysloader):
    class ms(System):

        class grp2(Group):
            s = UserBoolSensor()
            s2 = UserBoolSensor()
            a = BoolActuator()

        b = BoolActuator()

        class grp(Group):
            p = Program(priority=2.0,
                        active_condition=And(Or('s', 's2')),
                        on_activate=Run(Run(SetStatus('a', 's'))),
                        update_condition=Run(Run(SetStatus('a', 's'))),
                        )

    s = sysloader.new_system(ms)
    p = s.p
    assert isinstance(p.on_activate[0][0][0], BoolActuator)
    assert isinstance(p.on_activate[0][0][1], UserBoolSensor)
    assert isinstance(p.update_condition[0][0][0], BoolActuator)
    assert isinstance(p.update_condition[0][0][1], UserBoolSensor)
    assert isinstance(p.active_condition[0][0], UserBoolSensor)
    assert isinstance(p.active_condition[0][1], UserBoolSensor)


def test_update_on_activate(mysys):
    a1 = mysys.a1
    dp = a1.default_program
    assert a1.program_status[dp] == False
    assert repr(dp.on_activate) == "SetStatus('a1', Value(False))"
    dp.on_activate = SetStatus(a1, True)
    mysys.flush()
    assert a1.program_status[dp] == True


@pytest.yield_fixture
def freezesys(request):
    class sys(System):
        s1 = UserBoolSensor()
        p1 = Program(
            active_condition=Value(s1),
            on_activate=SetStatus(s1, 1)
        )
    s = sys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()


@pytest.yield_fixture(params=[UserBoolSensor, BoolActuator])
def freezesys2(request):
    class sys(System):
        s = request.param()
        p = Program(on_update=SetStatus(s, 1), triggers=[s])

    s = sys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()


def test_freeze2(freezesys2):
    assert freezesys2


def test_freeze(freezesys):
    freezesys.s1.status = 1
    freezesys.flush()
    assert freezesys.s1.status == True


@pytest.yield_fixture
def freezesys_act(request):
    class sys(System):
        s1 = UserBoolSensor()
        a1 = BoolActuator()
        a2 = BoolActuator()
        p1 = Program(
            update_condition=Or(s1, a1),
            on_activate=Run(
                SetStatus(a1, s1),
                SetStatus(a2, a1),
                SetStatus(a1, s1),
                SetStatus(a2, a1),
            )
        )
    s = sys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()

#@pytest.mark.skipif(True)


def test_freeze_act(freezesys_act):
    freezesys = freezesys_act
    freezesys.s1.status = 1
    freezesys.flush()
    assert freezesys.s1.status == True


class TestProgramFeatures(object):

    def test_triggerlist_targetlist_change(self, mysys):
        p = mysys.p
        #add = {p} if isinstance(p, StatusObject) else set()
        add = set()

        assert p.actual_triggers == set() | add
        p.active_condition = Value(mysys.s1)
        assert p.actual_triggers == {mysys.s1} | add
        p.on_activate = SetStatus(mysys.a1, Value(True))
        assert p.actual_triggers == {mysys.s1} | add
        assert p.actual_targets == {mysys.a1}
        assert mysys.a1.status == False
        mysys.s1.set_status(True)
        mysys.worker_thread.flush()
        assert mysys.a1.status == True
        p.targets = [mysys.a2]
        assert set(p.actual_targets) == {mysys.a1, mysys.a2}
        p.triggers = [mysys.s2]
        assert set(p.actual_triggers) == {mysys.s1, mysys.s2}
        p.triggers = []
        p.targets = []
        assert set(p.actual_targets) == {mysys.a1}
        assert set(p.actual_triggers) == {mysys.s1}
        p.targets = ['a2']
        assert set(p.actual_targets) == {mysys.a1, mysys.a2}
        p.triggers = ['s2']
        assert set(p.actual_triggers) == {mysys.s1, mysys.s2}
        p.exclude_triggers = ['s1']
        assert set(p.actual_triggers) == {mysys.s2}
        p.exclude_triggers = [mysys.s1]
        assert set(p.actual_triggers) == {mysys.s2}

    def test_triggerlist_targetlist_change2(self, mysys):
        p = mysys.p
        #add = {p} if isinstance(p, StatusObject) else set()
        add = set()
        assert set(p.actual_triggers) == add
        for i in ['on_update', 'on_activate', 'update_condition', 'on_deactivate', 'active_condition']:
            setattr(p, i, Value(mysys.s1))
            assert p.actual_triggers == {mysys.s1} | add
        for i in ['on_update', 'on_activate', 'on_deactivate']:
            setattr(p, i, SetStatus(mysys.a1, mysys.s1))
            assert p.actual_triggers == {mysys.s1} | add
            assert p.actual_targets == {mysys.a1}

    def test_triggerlist_targetlist_change2_namever(self, mysys):
        # TODO: investigate failure in https://travis-ci.org/tuomas2/automate/jobs/245124552
        # TODO: check also similar tests above.
        p = mysys.p
        #add = {p} if isinstance(p, StatusObject) else set()
        add = set()
        assert set(p.actual_triggers) == add
        for i in ['on_update', 'on_activate', 'update_condition', 'on_deactivate', 'active_condition']:
            setattr(p, i, Value('s1'))
            assert p.actual_triggers == {mysys.s1} | add
        for i in ['on_update', 'on_activate', 'on_deactivate']:
            setattr(p, i, SetStatus('a1', 's1'))
            assert p.actual_triggers == {mysys.s1} | add
            assert p.actual_targets == {mysys.a1}

    def test_program_priorities(self, mysys):
        p1, p2 = mysys.p1, mysys.p2
        dp = mysys.a1.program_stack[0]
        mysys.s1.set_status(True)
        mysys.s2.set_status(False)
        mysys.worker_thread.flush()
        assert p1.actual_targets == set()
        p1.active = False  # on activate triggers only when activation
        # really changes. So, only changing on_activate doesn't trigger
        # it unless deactivation takes place. It's correct
        # this way, I think.

        p1.on_activate = SetStatus(mysys.a1, mysys.s1)
        mysys.flush()
        assert p1.active
        assert p1.actual_targets == {mysys.a1}
        assert mysys.a1.program_stack == [dp, p1]
        assert mysys.a1.program == p1
        assert mysys.a1.status == mysys.s1.status == True

        p2.active = False
        p2.on_activate = SetStatus(mysys.a1, mysys.s2)
        assert mysys.a1.program == p2
        assert mysys.a1.program_stack == [dp, p1, p2]
        mysys.flush()
        assert mysys.a1.status == False
        p2.priority = 0.5
        assert mysys.a1.program == p1
        assert mysys.a1.program_stack == [dp, p2, p1]
        mysys.flush()
        assert mysys.a1.status == True
        p1.priority = -1
        p2.priority = -2
        assert mysys.a1.program == dp
        assert mysys.a1.program_stack == [p2, p1, dp]
        mysys.flush()
        assert mysys.a1.status == False


def test_logicstr(mysys):
    assert mysys.p2.active_condition_str == 'Value(True)'
    assert mysys.p2.active_condition == Value(True)
    mysys.p2.active_condition_str = 'Value(False)'
    assert mysys.p2.active_condition_str == 'Value(False)'
    assert mysys.p2.active_condition == Value(False)
    from traits.api import TraitError
    with pytest.raises(TraitError):
        mysys.p2.active_condition_str = 'asfdjk'
    assert mysys.p2.active_condition_str == 'Value(False)'

    assert mysys.p3.targets_str in ['TraitSetObject()', 'TraitSetObject([])']
    assert mysys.p3.targets == set([])
    mysys.p3.targets_str = '{a1}'
    assert mysys.p3.targets_str in ["TraitSetObject(['a1'])", "TraitSetObject({'a1'})"]
    assert mysys.p3.targets == {mysys.a1}
