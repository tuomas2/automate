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
from __future__ import print_function
from builtins import range
from builtins import object
import pytest
import mock

from automate import *
from automate.program import Program
from automate.statusobject import AbstractSensor
import time


ORIGVAL = 1.25
NEWVAL = 2.0


@pytest.yield_fixture(params=[0, 1])
def mysys(request):
    if request.param == 0:
        class _mysys(System):
            act = FloatActuator(default=ORIGVAL)
            a2 = FloatActuator(default=ORIGVAL)
            sens = UserBoolSensor(default=False)
            prog = Program(
                active_condition=Value(sens),
                on_activate=SetStatus(act, NEWVAL),
            )
    else:
        class _mysys(System):
            act = FloatActuator(default=ORIGVAL)
            a2 = FloatActuator(default=ORIGVAL)
            sens = UserBoolSensor(default=False)
            prog = Program(
                active_condition=Value('sens'),
                on_activate=SetStatus('act', NEWVAL),
            )
    sys = _mysys(exclude_services=['TextUIService'])
    sys.flush()
    yield sys
    sys.cleanup()


@pytest.yield_fixture
def prog(request):
    class _mysys(System):
        act = FloatActuator(default=ORIGVAL)
        a2 = FloatActuator(default=ORIGVAL)
        sens = UserBoolSensor(default=False)
        prog = Program(
            active_condition=Value(sens),
            on_activate=SetStatus(act, NEWVAL),
        )
    sys = _mysys(exclude_services=['TextUIService'])
    sys.flush()
    yield sys.prog
    sys.cleanup()


def test_oftypes(sysloader):
    class _mysys(System):
        act = FloatActuator(default=ORIGVAL)
        a2 = FloatActuator(default=ORIGVAL)
        sens = UserBoolSensor(default=False)
        prog = Program(
            active_condition=OfType(FloatActuator),
        )
        prog2 = Program(
            active_condition=And(sens, 'all_floatactuators'),
        )
        prog3 = Program(
            active_condition=And(sens, OfType(FloatActuator, exclude=[a2])),
        )
        prog4 = Program(
            priority=2.0,
            active_condition=Value(sens),
            on_activate=SetStatus(OfType(FloatActuator, type='targets'), 3.0),
        )
        all_floatactuators = OfType(AbstractActuator)
        prog5 = Program(
            on_activate=Run(SetStatus(all_floatactuators, all_floatactuators)),
        )

    sys = sysloader.new_system(_mysys)
    assert sys.prog3.actual_triggers == {sys.act, sys.sens}
    assert sys.prog2.actual_triggers == {sys.act, sys.a2, sys.sens}
    assert sys.prog.actual_triggers == {sys.act, sys.a2}
    sys.prog.active_condition = OfType(FloatActuator, UserBoolSensor)
    assert sys.prog.actual_triggers == {sys.act, sys.a2, sys.sens}
    assert sys.prog4.actual_targets == {sys.act, sys.a2}
    assert sys.prog4.actual_triggers == {sys.sens}
    sys.sens.status = 1
    sys.flush()
    assert sys.prog4 in sys.act.program_stack
    assert sys.prog4 in sys.a2.program_stack
    assert sys.prog4 == sys.act.program
    assert sys.prog4 == sys.a2.program
    assert sys.act.status == 3.0
    assert sys.a2.status == 3.0
    sys.prog.active_condition = OfType(FloatActuator, UserBoolSensor, exclude=[sys.sens])
    assert sys.prog.actual_triggers == {sys.act, sys.a2}


def test_call_eval(mysys):
    call_eval = mysys.prog.active_condition.call_eval
    #assert call_eval(lambda x: x + 1, 1) == 2
    assert call_eval(1, 1) == 1

    assert call_eval(mysys.act, mysys.prog) == mysys.act._status
    assert call_eval(1, mysys.prog) == 1


class TestAbstractLogicCallable(object):

    #    @mock.patch.object(Attrib, '_give_triggers')
    #    @mock.patch.object(Empty, '_give_triggers')
    #    def test_collect(self, mock_empty, mock_attrib, mysys):
    #        mock_empty.return_value = [mysys.sens, 1]
    #        mock_attrib.return_value = [mysys.act, mysys.act, 2, 3]
    #        c = Empty()
    #        c2 = Attrib()
    #        assert c.collect_triggers() == {mysys.sens}
    #
    #        c._args = [c2]
    #        assert c.collect_triggers() == {mysys.sens, mysys.act}
    #
    #        mock_attrib.return_value = [mysys.act]
    #        assert c.collect_triggers() == {mysys.sens, mysys.act}
    #
    #        mock_attrib.return_value = [mysys.sens]
    #        assert c.collect_triggers() == {mysys.sens}
    #
    #        mock_attrib.return_value = [1, 2, 3, 4, 5]
    #        assert c.collect_triggers() == {mysys.sens}

    def test_collect_real(self, mysys):
        mysys.prog.on_activate = c = Run(SetStatus(mysys.act, mysys.sens), Changed(mysys.sens))
        assert c.triggers == {mysys.sens}
        assert c.targets == {mysys.act}

    def test_collect_real2(self, mysys):
        mysys.prog.on_activate = c = Anything(mysys.act, Anything(mysys.act, mysys.sens))
        assert c.triggers == {mysys.act, mysys.sens}
        c[1]._args.remove(mysys.sens)
        assert c.triggers == {mysys.act}
        c[1]._args.append(mysys.sens)
        assert c.triggers == {mysys.act, mysys.sens}

    @pytest.mark.parametrize('x,strver',
                             [
                                 (
                                     Empty(),
                                     'Empty()'
                                 ),
                                 (
                                     Attrib('hep', 'tstattr'),
                                     "Attrib('hep', 'tstattr')"
                                 ),
                                 (
                                     Eval('print time.{param}()', 'import time', param='time'),
                                     "Eval('print time.{param}()', 'import time', param='time')"
                                 ),
                                 (
                                     Method([1], 'pop'),
                                     "Method([1], 'pop')"
                                 ),
                                 (
                                     Method([1], 'pop', arg1='hep'),
                                     "Method([1], 'pop', arg1='hep')",
                                 ),
                                 (
                                     SetStatus(1, 2),
                                     "SetStatus(1, 2)",
                                 ), ])
    def test_give_str2(self, x, strver, sysloader):
        class syst(System):
            c1 = UserAnySensor(on_deactivate=SetStatus('c1', x))
        s = sysloader.new_system(syst)

        c2 = s.c1.on_deactivate[1]
        if sys.version_info < (3, 0):
            strver = re.sub(r"([= \(])(['\"])", lambda m: m.group(1) + 'u' + m.group(2), strver)
        assert c2.give_str() == strver
        assert repr(c2) == strver
        assert str(c2) == strver

    def test_cancel(self):
        c = Empty()
        c2 = mock.create_autospec(Empty)
        c2.triggers = {}
        c2.targets = {}
        c2.set_system = lambda x: None

        c._args = [c2, 1, 2]
        c.cancel(None)
        assert c2.cancel.call_count == 1
        c._args[1] = c2
        c.cancel(None)
        assert c2.cancel.call_count == 2


def test_empty():
    c = Empty()
    assert c.value is None
    assert c._args == []
    assert c.collect_targets() == set()
    assert c.collect_triggers() == set()
    assert c.objects == []
    assert c.call(prog) is None
    assert c.call(1) is None


def test_call(prog):

    l = [0, 1]
    prog.on_activate = c = Method(l, 'pop', 0, no_caller=True)
    assert c.call(prog) == 0
    assert c.call(prog) == 1
    with pytest.raises(IndexError):
        c.call(prog)

    class mycls(object):

        def fun(self, *args, **kwargs):
            return args, kwargs

    obj = mycls()
    prog.on_activate = c2 = Method(obj, 'fun', 0, no_caller=True)
    assert c2.call(prog) == ((0,), {})
    prog.on_activate = c3 = Method(obj, 'fun', 0, kwarg=1, no_caller=True)
    assert c3.call(prog) == ((0,), {'kwarg': 1})


def test_func(prog):
    flag = []

    def fnc(*args, **kwargs):
        assert args == (1,)
        assert kwargs == {'tst': 'hep'}
        flag.append(1)
    prog.on_deactivate = f = Func(fnc, 1, tst='hep')
    f.call(prog)
    assert flag
    prog.on_deactivate = f = Func(lambda: 1)
    f.call(prog)


def test_attrib(prog):
    l = [1, 2, 3]

    prog.on_activate = c = Attrib(l, "pop")
    assert c.call(prog)() == 3

    class mycls(object):
        a = 1
    obj = mycls()
    prog.on_activate = c2 = Attrib(obj, 'a')
    assert c2.call(prog) == 1

def test_attrib2(sysloader):
    class mysys2(System):
        class joku(object):
            joku = 2.0
        s = UserFloatSensor(default=3.0)
        a = FloatActuator()
        p = Program(active_condition=Attrib(joku, 'joku'))
        p2 = Program(active_condition=Attrib(p, 'active'))
        p3 = Program(active_condition=Value(True),
                     on_activate=SetStatus(a, Attrib(s, 'status', no_eval=True)))


    s = sysloader.new_system(mysys2)
    assert s.p.active
    assert s.p2.active
    s.flush()
    assert s.s in s.p3.actual_triggers
    assert s.a.program == s.p3
    assert s.a.status == 3.0


def test_onlytriggers(mysys):
    mysys.prog.on_activate = c = OnlyTriggers(mysys.act, mysys.sens)
    assert c.collect_targets() == set()
    assert c.collect_triggers() == {mysys.sens, mysys.act}


def test_log(caplog, mysys):
    mysys.prog.on_activate = c = Log("hephep")
    c.call(prog)
    assert "hephep" in caplog.text()  # logentries

    mysys.prog.on_activate = c = Log("hephep %s", 'hop')
    c.call(prog)
    assert 'hephep hop' in caplog.text()
    mysys.prog.on_activate = c = Log(mysys.sens)
    c.call(mysys.prog)
    assert str(mysys.sens._status) in caplog.text()

    caplog.setLevel(logging.INFO)
    mysys.prog.on_activate = c = Debug('debughep')
    c.call(prog)
    assert 'debughep' not in caplog.text()
    caplog.setLevel(logging.DEBUG)
    c.call(prog)
    assert 'debughep' in caplog.text()


@pytest.mark.parametrize('x,r', [
    (ToStr(1), '1'),
    (ToStr(1, 2, no_sub=True), '1 2'),
    (ToStr("hep"), 'hep'),
    (ToStr("hep", 1, no_sub=True), 'hep 1'),
    (ToStr("hep", "hop", no_sub=True), "hep hop"),
    (ToStr('Test {}', 1), 'Test 1'),
    (ToStr('Test {muu} {joku}', joku=1, muu=2), 'Test 2 1'),
])
def test_tostr(sysloader, x, r):
    class syst(System):
        c1 = UserAnySensor(on_activate=SetStatus('c1', x))
    s = sysloader.new_system(syst)
    assert s.c1.status == r


def test_eval():
    c = Eval('a+1', pre_exec='a=1')
    assert c.call(prog) == 2
    c = Eval('a+1+{b}', pre_exec='a=1', b=1)
    assert c.call(prog) == 3
    assert Eval('class hep:\n    pass').call(prog) == True


@pytest.mark.parametrize('x, r', [
    (Shell('true'), 0),
    (Shell('false'), 1),
    (Shell('somecommandthatcannotbefound'), 127),
    (Shell('echo hep', output=True), 'hep\n'),
    (Shell('cat', output=True, input='hep\n'), 'hep\n'),
])
def test_shell(x, r, sysloader):
    class mysys(System):
        p1 = UserAnySensor(on_activate=SetStatus('p1', x))
    s = sysloader.new_system(mysys)

    assert s.p1.status == r


@pytest.mark.parametrize('var', [1, 2, 0])
def test_setstatus(mysys, var):
    mysys.sens.set_status(1)  # set program active
    mysys.flush()
    assert mysys.prog.active
    s = SetStatus(mysys.act, var)
    s.setup_callable_system(mysys)
    s.call(mysys.prog)
    assert s.collect_targets() == {mysys.act}
    assert s.collect_triggers() == set()
    mysys.flush()
    assert mysys.act._status == var


@pytest.mark.parametrize('var', [0, 1, [1] * 2, [2, 3]])
def test_setvalues(mysys, var):
    assert not mysys.prog.active
    mysys.prog.on_activate = s = SetStatus([mysys.act, mysys.a2], var)
    assert s.collect_targets() == {mysys.act, mysys.a2}
    assert s.collect_triggers() == set()
    mysys.sens.set_status(1)  # set program active
    mysys.flush()
    assert mysys.prog.active
    var = [var] if not isinstance(var, list) else var
    assert mysys.act._status == var[0]
    assert mysys.a2._status == var[-1]


def test_setvalue_call(mysys):
    assert not mysys.prog.active

    def func():
        return [2, 3]
    mysys.prog.on_activate = s = SetStatus([mysys.act, mysys.a2], Func(func))
    assert s.collect_targets() == {mysys.act, mysys.a2}
    assert s.collect_triggers() == set()
    mysys.sens.set_status(1)  # set program active
    mysys.flush()
    assert mysys.prog.active
    assert mysys.act._status == 2
    assert mysys.a2._status == 3


def test_setvalue_call2(mysys):
    assert not mysys.prog.active

    def targets():
        return [mysys.act, mysys.a2]

    def values():
        return [2, mysys.sens]
    mysys.prog.on_activate = s = SetStatus(Func(targets), Func(values))
    mysys.prog.targets = {mysys.act, mysys.a2}
    mysys.sens.set_status(1)  # set program active
    mysys.flush()
    assert mysys.prog.active
    assert mysys.act._status == 2
    assert mysys.a2._status == mysys.sens.status


def test_func_arguments_translated(sysloader):
    returnvalue = []

    def testfunc(arg, test=1, test2=1):
        returnvalue.append((arg, test, test2))

    class ms(System):
        f = UserFloatSensor(active_condition=Value('f'), on_activate=Func(testfunc, 'f', test='f', test2=Mult(2, 'f')))

    s = sysloader.new_system(ms)
    s.f.status = 2.3
    s.flush()
    assert returnvalue[0] == (s.f.status, s.f.status, 2 * s.f.status)

# def test_waituntil_blocking(sysloader):
#    class ms(System):
#        s = UserFloatSensor()
#        f = UserFloatSensor(active_condition=Value('f'), on_activate=Run(SetStatus('t2', 1), Threaded(WaitUntil(s, SetStatus('t', 1), block=True))))
#        t = UserFloatSensor()
#        t2 = UserFloatSensor()
#    s = sysloader.new_system(ms)
#    s.f.status = 1
#    s.flush()
#    assert s.t2.status == 1
#    assert s.t.status == 0
#    s.s.status=1
#    s.flush()
#    assert s.t.status == 1


def test_waituntil_noblock(sysloader):
    class ms(System):
        s = UserFloatSensor()
        f = UserFloatSensor(active_condition=Value('f'), on_activate=Run(
            SetStatus('t2', 1), WaitUntil(s, SetStatus('t', 1))))
        t = UserFloatSensor()
        t2 = UserFloatSensor()
    s = sysloader.new_system(ms)
    s.f.status = 1
    s.flush()
    assert s.t2.status == 1
    assert s.t.status == 0
    s.s.status = 1
    s.flush()
    assert s.t.status == 1


def test_waituntil_two(sysloader):
    f1, f2 = [], []

    def func1():
        f1.append(1)

    def func2():
        f2.append(1)

    class ms(System):
        s = UserFloatSensor()
        s2 = UserFloatSensor()

        f = UserFloatSensor(active_condition=Value('f'),
                            on_activate=WaitUntil(s, Func(func1)))
        f2 = UserFloatSensor(active_condition=Value('f2'),
                             on_activate=WaitUntil(s2, Func(func2)))

    s = sysloader.new_system(ms)
    assert not f1
    assert not f2
    s.f.status = 1
    s.flush()
    assert not f1
    assert not f2
    s.s.status = 1
    s.flush()
    assert f1
    assert not f2
    s.f2.status = 1
    s.flush()
    assert f1
    assert not f2
    s.s2.status = 1
    s.flush()
    assert f1
    assert f2
    s.f.status = 0
    s.f2.status = 0
    s.s.status = 0
    s.s2.status = 0
    f1.pop(), f2.pop()
    s.flush()
    s.f.status = 1
    assert not f1 and not f2
    s.flush()
    s.f2.status = 1
    assert not f1 and not f2
    s.flush()
    s.s.status = 1
    s.flush()
    assert f1 and not f2
    s.s2.status = 1
    s.flush()
    assert f1 and f2


def test_waituntil_cancel(sysloader):
    class ms(System):
        s = UserFloatSensor()
        f = UserFloatSensor(active_condition=Value('f'), on_activate=Run(
            SetStatus('t2', 1), WaitUntil(s, SetStatus('t', 1))))
        t = UserFloatSensor()
        t2 = UserFloatSensor()
    s = sysloader.new_system(ms)
    s.f.status = 1
    s.flush()
    assert s.t2.status == 1
    assert s.t.status == 0
    s.f.status = 0  # deactivating program -> should cancel waituntil
    s.flush()
    assert s.t.status == 0
    s.s.status = 1
    s.flush()
    assert s.t.status == 0  # -> so that this is still unchanged
    s.f.status = 1
    s.flush()
    assert s.t.status == 1


def test_waituntil_musicserver_case(sysloader):
    """
        This test was created to debug/investigate my own program.
        I'll leave this as a test now that it works as expected.
    """
    called = []

    def start_playback(volume_status):
        called.append(volume_status)

    class ms(System):
        reset_mplayer = (
            If(Not('out_actual'),
               Run(
                SetStatus('launchtime', 1),
                WaitUntil('soundcard_ready',
                          SetStatus('volume', 0),
                          SetStatus('volume', 10),
                          SetStatus('launchtime', 0),
                          ),
            )
            ))
        start = UserBoolSensor(
            active_condition=Value('start'),
            on_activate=Run('reset_mplayer',
                            WaitUntil(And('soundcard_ready', Not('launchtime')),
                                      Func(start_playback, 'volume'),
                                      SetStatus('start', 0))))

        volume = UserIntSensor()

        out_actual = BoolActuator(
            active_condition=Value('out_actual'),
            on_activate=SetStatus('soundcard_ready', 1)
        )

        launchtime = UserBoolSensor()

        out_buf_prog = Program(
            on_update=SetStatus('out_buffer', 'launchtime')
        )

        out_buffer = BoolActuator(
            on_update=SetStatus(out_actual, 'out_buffer'),
        )

        soundcard_ready = UserBoolSensor()

    s = sysloader.new_system(ms)
    s.start.status = 1
    s.flush()
    assert s.start.status == 0
    assert 10 in called  # ensure that volume was set before starting playback
    assert s.soundcard_ready.status


def test_waituntil_func_called(sysloader):
    called = []

    def myfunc():
        called.append(1)

    class ms(System):
        s = UserFloatSensor(active_condition=Value('s'),
                            on_activate=WaitUntil(Not('f'), Func(myfunc))
                            )
        s2 = UserFloatSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=Run(
                SetStatus('t2', 1),
                WaitUntil(
                    And(s, s2),
                    SetStatus('t', 1),
                    SetStatus('f', 0)
                )
            )
        )
        t = UserFloatSensor()
        t2 = UserFloatSensor()
    s = sysloader.new_system(ms)
    s.f.status = 1
    s.flush()
    assert s.t2.status == 1
    assert s.t.status == 0
    s.s.status = 1
    s.flush()
    assert s.t.status == 0
    s.s2.status = 1
    s.flush()
    assert s.t.status == 1
    assert called


def test_waituntil_callable(sysloader):
    class ms(System):
        s = UserFloatSensor()
        s2 = UserFloatSensor()
        f = UserFloatSensor(active_condition=Value('f'), on_activate=Run(
            SetStatus('t2', 1), WaitUntil(And(s, s2), SetStatus('t', 1))))
        t = UserFloatSensor()
        t2 = UserFloatSensor()
    s = sysloader.new_system(ms)
    w = s.f.on_activate[1]
    s.f.status = 1
    s.flush()
    assert s.t2.status == 1
    assert s.t.status == 0
    s.s.status = 1
    s.flush()
    assert s.t.status == 0
    s.s2.status = 1
    assert w.get_state(s.f).callbacks
    s.flush()
    assert s.t.status == 1
    assert not w.get_state(s.f).callbacks


def test_while_actuator_condition(sysloader):
    called = []

    def myfunc():
        called.append(1)

    class ms(System):
        s = IntActuator(default=0)

        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(s < 3, Func(myfunc), SetStatus(s, Add(s, 1)), do_after=SetStatus('f', 0))
        )
    s = sysloader.new_system(ms)
    s.f.status = 1
    # Flushing system is not sufficient because While is threaded activity.
    time.sleep(0.5)
    assert s.f.status == 0
    #assert s.s.program_status(s.f) == 3
    assert s.s.status == 0
    assert len(called) == 3


def test_while_akvadimmer(sysloader):
    called = []

    def myfunc():
        called.append(1)

    class ms(System):
        warm_lamp_out = FloatActuator(default=0.)
        cold_lamp_out = FloatActuator(default=0.)

        fd_mpl = UserFloatSensor(description='multiplier', default=0.7)
        fd_thr = UserFloatSensor(description='threshold', default=0.1)
        fd_slp = UserFloatSensor(description='sleep time', default=0.0)

        dimmer = While(
            Or(
                Value('cold_lamp_out'),
                Value('warm_lamp_out'),
            ),
            SetStatus('cold_lamp_out', IfElse(Value('cold_lamp_out') > Value(fd_thr),
                                              Value('cold_lamp_out') * Value(fd_mpl), 0)),
            SetStatus('warm_lamp_out', IfElse(Value('warm_lamp_out') > Value(fd_thr),
                                              Value('warm_lamp_out') * Value(fd_mpl), 0)),
            Func(time.sleep, 'fd_slp'),
            Func(myfunc),
            do_after=Run(SetStatus(['akvadimmer', 'fade_out'], [0] * 2))
        )

        warm_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=1, user_editable=False)
        cold_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=1., user_editable=False)

        fade_out = UserBoolSensor(priority=3,
                                  active_condition=Value('fade_out'),
                                  on_activate=Run('dimmer')
                                  )

        akvadimmer = UserBoolSensor(priority=1.,  # lower priority light for aquarium (raspi1) remote use only
                                    active_condition=Value('akvadimmer'),
                                    on_activate=IfElse(
                                        # if lamp already on, do not activate this function at all
                                        Or('warm_lamp_out', 'cold_lamp_out'),
                                        SetStatus('akvadimmer', 0),
                                        Run(SetStatus('warm_lamp_out', 'warm_preset_akva'),
                                            SetStatus('cold_lamp_out', 'cold_preset_akva'),
                                            Run('dimmer'),
                                            )
                                    ))

    s = sysloader.new_system(ms)
    s.akvadimmer.status = 1
    # Flushing system is not sufficient because While is threaded activity.
    time.sleep(0.5)
    assert len(called) == 8
    assert s.dimmer[0].status == False
    assert s.akvadimmer.status == 0


def test_while_basic(sysloader):
    called = []

    def myfunc():
        called.append(1)

    class ms(System):
        s = UserIntSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(Less(s, 3), Func(myfunc), SetStatus(s, Add(s, 1)))
        )
    s = sysloader.new_system(ms)
    s.f.status = 1
    # Flushing system is not sufficient because While is threaded activity.
    time.sleep(0.5)
    assert s.s.status == 3
    assert len(called) == 3


def test_while_do_after(sysloader):
    called = []
    do_after_called = []

    def myfunc():
        called.append(1)

    def do_after():
        do_after_called.append(1)

    class ms(System):
        s = UserIntSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(Less(s, 3), Func(myfunc), SetStatus(s, Add(s, 1)), do_after=Func(do_after))
        )
    s = sysloader.new_system(ms)
    s.f.status = 1
    # Flushing system is not sufficient because While is threaded activity.
    time.sleep(0.5)
    assert s.s.status == 3
    assert len(called) == 3
    assert do_after_called


def test_while_cancel(sysloader, caplog):
    called = []

    def myfunc():
        time.sleep(0.1)
        called.append(1)

    class ms(System):
        s = UserIntSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(Value(True), Func(myfunc), SetStatus(s, Add(s, 1)))
        )
    s = sysloader.new_system(ms)
    w = s.f.on_activate
    assert not w.get_state(s.f).threads
    s.f.status = 1
    s.flush()
    assert w.get_state(s.f).threads
    s.f.status = 0  # : Deactivates program => cancels action
    s.flush()
    #assert w.get_state(s.f).threads[0]._cancel_while
    # TODO: this test fails too often on Travis CI
    time.sleep(0.5)
    assert not w.get_state(s.f)
    assert 'Canceling While' in caplog.text()


def test_while_nested(sysloader):
    called = []

    def myfunc(s, s2):
        called.append((s, s2))

    class ms(System):
        s = UserIntSensor()
        s2 = UserIntSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(s < 3, While(s2 < 3, Func(myfunc, s, s2), SetStatus(s2, Add(s2, 1))), SetStatus(s, s + 1))
        )
    s = sysloader.new_system(ms)
    s.f.status = 1
    s.flush()
    time.sleep(0.5)
    assert s.s.status == 3
    assert s.s2.status == 3


def test_while_nested_cancel(sysloader):
    called = []

    def myfunc(s, s2):
        called.append((s, s2))
        time.sleep(0.1)

    class ms(System):
        s = UserIntSensor()
        s2 = UserIntSensor()
        f = UserFloatSensor(
            active_condition=Value('f'),
            on_activate=While(s < float('inf'),
                              While(s2 < float('inf'),
                                    Func(myfunc, s, s2),
                                    SetStatus(s2, Add(s2, 1))),
                              SetStatus(s, s + 1))
        )
    s = sysloader.new_system(ms)
    w1 = s.f.on_activate
    w2 = w1[1]
    s.f.status = 1
    s.flush()
    time.sleep(0.5)
    assert len(w1.get_state(s.f).threads) == 1
    #assert len(w2.get_state(s.f).threads)==1
    assert not w1.get_state(s.f).threads[0]._cancel_while
    #assert not w2.get_state(s.f).cancel
    s.f.status = 0
    s.flush()
    with w1._lock:
        assert (w1.get_state(s.f).threads and w1.get_state(s.f).threads[0]._cancel_while) or not w1.get_state(s.f)
    # There are many threads of second while, so this is not so easy to test
    # with w2._lock:
    #    assert (w2.get_state(s.f).cancel and w2.get_state(s.f).threads) or not w2.get_state(s.f)
    time.sleep(0.5)
    assert not w1.get_state(s.f)
    assert not w2.get_state(s.f)
    assert s.s.status > 0
    assert s.s2.status > 0


def get_musicserver():
    def func(arg1, arg2=None):
        print(arg1, arg2)  # getattr(arg2, 'name', None)

    class MusicServer_Tests(System):
        normal_volume = UserIntSensor(
            default=65,
            value_min=0,
            value_max=100,
        )
        piano_volume = UserIntSensor(
            default=30,
            value_min=0,
            value_max=100,
        )

        israspi = Value(True)
        email_sender = Empty()

        class UrlPlay(Group):
            reset_mplayer = Run(
                If(Not('out_actual'),
                   Func(func, 'launchtime<-1', TriggeredBy(), return_value=False),
                   SetStatus('launchtime', 1),
                   WaitUntil('soundcard_ready',
                             SetStatus('volume', 0),
                             SetStatus('volume', IfElse('piano_on', 'piano_volume', 'normal_volume')),
                             SetStatus('launchtime', 0),
                             Func(func, 'launchtime <-0'),
                             ),
                   ),
                Empty('mpc pause'),
                If('mplayer_pid',
                   Empty('kill mplayer...'),
                   SetStatus('mplayer_pid', 0)
                   )
            )

            mplayer_pid = UserIntSensor(user_editable=False)

            mplayer = UserStrSensor(
                active_condition=Value('mplayer'),
                exclude_triggers=['piano_volume', 'normal_volume'],  # launchtime', 'out_actual', 'soundcard_ready'],
                on_update=Run(
                    Func(func, 'mplayer Before triggered_by', TriggeredBy(), return_value=False),
                    If(TriggeredBy('mplayer'),
                       Run(reset_mplayer),
                       Func(func, 'mplayer waituntil init', TriggeredBy(), return_value=False),
                       WaitUntil(And('soundcard_ready', Not('launchtime')),
                                 Func(func, 'mplayer waituntil through'),
                                 SetStatus(mplayer_pid, 1)
                                 )
                       ),
                )
            )

        class Commands(Group):
            tags = 'web'

            radiodei = UserEventSensor(
                on_activate=SetStatus('mplayer', 'mms://mms.radiodei.fi/RadioDeiR2HF')
            )

            start = UserBoolSensor(
                active_condition=Value('start'),
                on_activate=Run('reset_mplayer',
                                WaitUntil(And('soundcard_ready', Not('launchtime')),
                                          Empty('mpc play'),
                                          SetStatus('start', 0))
                                )
            )

            stop = UserEventSensor(
                on_activate=Run('reset_mplayer', 'clear'),
            )

            volume = UserIntSensor(
                default=60,
                value_min=0,
                value_max=100,
            )

            manual_mode = UserBoolSensor(
                default=False,
            )

        class In(Group):
            soundcard_ready = UserBoolSensor(
                active_condition=Value('soundcard_ready'),
                on_activate=SetStatus('volume', IfElse('piano_on', 'piano_volume', 'normal_volume')),
            )

            playback_active = UserBoolSensor()

            set_piano_volume = Program(
                active_condition=And('piano_on', 'soundcard_ready'),
                on_activate=SetStatus('volume', 'piano_volume'),
                on_deactivate=SetStatus('volume', 'normal_volume')
            )

        class Out(Group):
            launchtime = UserBoolSensor()
            piano_on = UserBoolSensor()
            gmediarender_pid = UserIntSensor(default=0, user_editable=False)
            out_actual = BoolActuator(
                active_condition=Value('out_actual'),
                on_activate=SetStatus('gmediarender_pid', 1),
                on_deactivate=If('gmediarender_pid',
                                 Run(Empty(),
                                     SetStatus('gmediarender_pid', 0))),
            )

            out_buf_prog = Program(
                on_update=SetStatus('out_buffer', Or('launchtime', 'playback_active', 'piano_on', 'manual_mode'))
            )

            out_buffer = BoolActuator(
                safety_mode='both',
                change_delay=900.0,
                change_mode='falling',
                on_update=SetStatus(out_actual, 'out_buffer'),
            )
    return MusicServer_Tests


def test_musicserver_start(sysloader):
    s = sysloader.new_system(get_musicserver())
    assert not s.out_buffer.status
    s.start.status = True
    s.flush()
    assert s.out_buffer.status
    assert s.start.status
    assert s.launchtime.status
    s.soundcard_ready.status = 1
    # s.launchtime.status=False
    s.flush()
    assert not s.launchtime.status
    assert not s.start.status


def test_musicserver_radiodei(sysloader):
    s = sysloader.new_system(get_musicserver())
    reset_mplayer_waituntil_soundcard_ready = s.reset_mplayer[0][3]
    mplayer_on_update_waituntil = s.mplayer.on_update[1][3]

    assert s.mplayer.on_update.triggers == set()  # {s.piano_volume, s.normal_volume}
    assert mplayer_on_update_waituntil.triggers == set()  # s.launchtime, s.soundcard_ready}
    assert isinstance(mplayer_on_update_waituntil, WaitUntil)
    assert isinstance(reset_mplayer_waituntil_soundcard_ready, WaitUntil)
    assert not reset_mplayer_waituntil_soundcard_ready.state
    assert not mplayer_on_update_waituntil.state
    assert not s.out_buffer.status
    assert not s.out_actual.status
    assert not s.mplayer.status
    s.radiodei.status = True
    # mplayer <- url
    #    reset_mplayer
    #       launchtime <- 1
    #       waituntil soundcard_ready...
    #    waituntil soundcard_ready and not launchtime
    #
    s.flush()
    # there should be now a callback waiting in both of these waituntils.
    assert reset_mplayer_waituntil_soundcard_ready.state
    assert mplayer_on_update_waituntil.state
    assert s.mplayer.status  # contains url
    assert s.launchtime.status  # reset_mplayer switched this on
    assert s.out_buffer.status  # launchtime = 1 switched this on
    assert s.out_actual.status  # out_buffer turned this on
    # s.launchtime.status=False
    s.flush()
    s.soundcard_ready.status = 1
    # reset_mplayer should continue now and turn launchtime to 0
    s.flush()
    assert not s.launchtime.status
    assert s.out_buffer.status
    # also another waituntil should have run and set mplayer_pid <- 1
    assert s.mplayer_pid.status


def test_setattr(mysys):
    class mycls(object):
        a = 1
    a = mycls()
    mysys.prog.on_deactivate = c = SetAttr(a, b=2, c=3, d=mysys.sens)
    # c.setup_callable_system(mysys)
    c.call(prog)
    assert a.b == 2
    assert a.c == 3
    assert a.d == mysys.sens._status
    assert c.collect_triggers() == {mysys.sens}
    c._args[0] = mysys.act
    assert c.collect_targets() == {mysys.act}


def test_changed(mysys):
    mysys.prog.on_deactivate = c = Changed(mysys.sens)
    s = AbstractSensor(system=mysys, default=False)
    mysys.flush()
    assert s._status == False
    assert c.call(prog) == True
    assert c.call(prog) == False
    mysys.prog.on_update = Run(SetStatus(mysys.act, NEWVAL), SetStatus(s, c))
    mysys.sens.set_status(True)
    mysys.flush()
    assert s._status == True
    assert c.collect_targets() == set()
    assert c.collect_triggers() == {mysys.sens}


def test_swap(mysys):
    assert mysys.sens._status == 0
    assert mysys.act._status == 1.25
    mysys.prog.active_condition = Value(True)
    mysys.prog.update_condition = Value(True)
    mysys.prog.triggers = [mysys.sens]
    mysys.flush()
    assert mysys.sens._status == 0
    assert mysys.act._status == 2.0
    assert mysys.prog.active
    mysys.prog.on_update = Swap(mysys.act)
    mysys.flush()
    assert mysys.sens._status == 0
    assert mysys.act._status == 0
    mysys.sens.set_status(1)
    mysys.flush()
    assert mysys.act._status == 1
    mysys.sens.set_status(0)
    mysys.flush()
    assert mysys.act._status == 0
    #assert False


def test_run(prog):
    count = 0
    c1 = Exec('count += 1', namespace=locals())
    c = prog.on_deactivate = Run(c1, c1, c1)
    c.call(prog)
    assert c1._kwargs['namespace']['count'] == 3


def test_delay(caplog, mysys):
    c = Delay(0.05, Log('hep'))
    mysys.namespace['c'] = c
    c.call(prog)
    assert 'Scheduling' in caplog.text()
    time.sleep(1.5)
    print('2', caplog.text())
    assert 'Time is up' in caplog.text()


def test_delay_cancel(caplog, prog):
    c = Delay(1, Log('hep'))
    #mysys.namespace['c'] = c
    prog.on_activate = c
    c.call(prog)
    assert 'Scheduling' in caplog.text()
    assert c.get_state(prog).timers
    c.cancel(prog)
    time.sleep(2)
    # print caplog.text()
    assert not c.get_state(prog)
    assert 'Cancelling Delay' in caplog.text()
    assert "Time is up" not in caplog.text()


# def test_delay_cancel(caplog):
#    c = Delay(0.05, Log('hep'))
#    c.call(prog)
#    assert 'Scheduling' in caplog.text()
#    assert c._timer
#    c.cancel()
#    assert not c._timer
#    time.sleep(0.1)
#    assert 'Cancelling Delay' in caplog.text()
#    assert "Time is up" not in caplog.text()


def test_delay_secondtry(caplog, mysys):
    """
    Now the definition is to run always, not cancel
    """
    mysys.prog.on_deactivate = c = Delay(0.05, Log('hep'))
    c.call(prog)
    assert 'Scheduling' in caplog.text()
    c.call(prog)
    assert len(c.get_state(prog).timers) == 2
    time.sleep(1.5)
    assert "Time is up" in caplog.text()
    assert len(c.get_state(prog).timers) == 0


def test_ifelse(mysys):
    class mycls(object):
        r = 0
    itm1 = mycls()
    itm2 = mycls()

    def reset():
        itm1.r = 0
        itm2.r = 0
    mysys.prog.on_deactivate = c1 = SetAttr(itm1, r=1)
    mysys.prog.on_deactivate = c2 = SetAttr(itm2, r=1)

    mysys.namespace['i1'] = i = IfElse(0, c1)
    i.call(prog)
    assert itm1.r == 0

    mysys.namespace['i2'] = i = IfElse(1, c1)
    i.call(prog)
    assert itm1.r == 1
    reset()

    mysys.namespace['i3'] = i = IfElse(0, c1, c2)
    i.call(prog)
    assert itm1.r == 0
    assert itm2.r == 1
    reset()

    mysys.namespace['i4'] = i = IfElse(1, c1, c2)
    i.call(prog)
    assert itm1.r == 1
    assert itm2.r == 0

    mysys.namespace['i5'] = _if = IfElse(mysys.sens, mysys.act, mysys.a2)
    assert _if.collect_triggers() == {mysys.act, mysys.a2}
    assert _if.collect_targets() == {mysys.act, mysys.a2}


@pytest.mark.parametrize('var', list(range(3)))
def test_switch(var, mysys):
    i = mysys.namespace['i'] = Switch(var, 1, 2, 3)
    i.call(prog) == var + 1
    mysys.prog.on_deactivate = c = Switch(mysys.sens, mysys.act)
    assert c.collect_targets() == {mysys.act}
    assert c.collect_triggers() == {mysys.act}


def test_switch_dict(sysloader):
    class mysys(System):
        a = IntActuator()
        s = UserStrSensor(active_condition=Value('s'),
                          on_update=Switch('s', {'cmd1': SetStatus(a, 1),
                                                 'cmd2': SetStatus(a, 2)
                                                 }
                                           ),
                          )
    s = sysloader.new_system(mysys)
    assert not s.s.active
    s.s.status = 'cmd1'
    s.flush()
    assert s.s.active
    assert s.s.on_update.collect_targets() == {s.a}
    assert s.s.actual_targets == {s.a}
    assert s.a.program == s.s
    assert s.a.status == 1
    s.s.status = 'cmd2'
    s.flush()
    assert s.a.status == 2


def test_tryexcept(prog):
    e1 = Eval('aslkfdj')
    e2 = Eval('1')
    e3 = Eval('2')
    c = prog.on_deactivate = TryExcept(e1, e2)
    assert c.call(prog) == 1
    c = prog.on_deactivate = TryExcept(e2, e3)
    assert c.call(prog) == 1

nums = [1, 5, -2]


@pytest.mark.parametrize('x,r', [
    (Min(*nums), min(nums)),
    (Max(*nums), max(nums)),
    (Sum(*nums),  sum(nums)),
    (Product(*nums), 1 * 5 * -2),
    (Mult(*nums), 1 * 5 * -2),
    (Add(*nums), sum(nums)),
])
def test_math(prog, x, r):
    prog.on_deactivate = c = x
    assert x.call(prog) == r


@pytest.mark.parametrize('x,r', [
    (Anything(0, 0, 0), True),
    (Anything(1, 0, 0), True),
    (Anything(1, 0, 1), True),
    (Or(1, 0, 1), True),
    (Or(0, 0, 0), False),
    (Or(1, 1, 1), True),

    (Or([0, 0, 0], 0, 1), True),
    (Or([0, 0, 1], 0, 0), True),

    (And(1, 1), True),
    (And(0, 1), False),
    (And(0, 0), False),
    (And([0, 0], 0), False),
    (And([1, 0], 0), False),
    (And([0, 0], 1), False),
    (And([1, 1], 0), False),
    (And([1, 1], 1), True),

    (Neg(0), 0),
    (Neg(1), -1),
    (Neg(-2), 2),
    (Not(0), True),
    (Not(1), False),
    (Equal(1, 1), True),
    (Equal(2, 1), False),
    (Equal(0, 0), True),

    (Less(0, 1), True),
    (Less(1, 1), False),
    (Less(1, 0), False),
    (More(0, 1), False),
    (More(1, 0), True),
    (More(1, 1), False),
    (Value(5), 5),
])
def test_logical(prog, x, r):
    prog.on_deactivate = x
    assert x.call(prog) == r


def test_logical2(prog):
    prog.on_deactivate = c = Neg(1, 1)
    with pytest.raises(AssertionError):
        c.call(prog)
    c = prog.on_deactivate = Not(1, 1)
    with pytest.raises(AssertionError):
        c.call(prog)


def test_logic_cmp():
    v1 = Value(1)
    v2 = Value(2)
    assert v1 * v2 == Product(v1, v2)
    assert v1 + v2 == Sum(v1, v2)
    assert v1 - v2 == Sum(v1, Neg(v2))
    assert -v1 == Neg(v1)
    assert (v1 < v2) == Less(v1, v2)
    assert (v1 > v2) == More(v1, v2)


@pytest.yield_fixture
def self_sys():
    class sys(System):
        s2 = UserBoolSensor()
        s = UserIntSensor(active_condition=Value('s'),
                          on_activate=SetStatus(['s', 's2'], [0, 1])
                          )
    s = sys(exclude_services=['TextUIService'])
    s.flush()
    yield s
    s.cleanup()


def test_self(self_sys):
    S = self_sys
    assert S.s.status == 0
    assert S.s2.status == False
    S.s.status = 1
    S.flush()
    assert S.s2.status == True
    assert S.s.status == 0


def test_self_delay(self_sys):
    S = self_sys
    S.s.on_activate = Delay(0.1, SetStatus('s', 0))
    assert S.s.status == 0
    S.s.status = 1
    S.flush()
    assert S.s.status == 1
    time.sleep(1.5)
    S.flush()
    assert S.s.status == 0


@pytest.mark.parametrize('x,r', [
    (RegexMatch(r'(\d*)(\w*)', '12test'), '12test'),
    (RegexSearch(r'(\d*)(\w*)', '12test'), '12'),

    (RegexMatch(r'(\d*)(\w*)', '12test', group=2), 'test'),
    (RegexSearch(r'(\d*)(\w*)', '12test', group=2), 'test'),


    (RegexMatch(r'testasfd', 'test'), ''),
    (RegexSearch(r'testasfd', 'test'), ''),

    (RegexMatch(r'heptest', 'heptest'), 'heptest'),
    (RegexSearch(r'heptest', 'heptest', group=0), 'heptest'),

    (RegexMatch(r'heptest1', 'heptest'), ''),
    (RegexSearch(r'heptest1', 'heptest'), ''),

    (RegexMatch(r'(hep)te(st1)', 'heptest1', group=1), 'hep'),
    (RegexSearch(r'(hep)te(st1)', 'heptest1', group=1), 'hep'),

    (RegexMatch(r'(hep)te(st1)', 'heptest1', group=2), 'st1'),
    (RegexSearch(r'(hep)te(st1)', 'heptest1', group=2), 'st1'),


])
def test_regex(x, r, sysloader):
    class mysys(System):
        p1 = UserAnySensor(on_activate=SetStatus('p1', x))
    s = sysloader.new_system(mysys)

    assert s.p1.status == r

# def test_regexmatch(sysloader):
#    class mysys(System):
#        p1 = UserBoolSensor(on_update=SetStatus('p1', RegexMatch('test', 'test')))
#        p2 = UserBoolSensor(on_update=SetStatus('p2', RegexMatch('testasfd', 'test')))
#        p3 = UserBoolSensor(on_update=SetStatus('p3', RegexMatch('^hep\w*$', 'heptest')))
#    s = sysloader.new_system(mysys)
#
#    assert s.p1.status == True
#    assert s.p2.status == False
#    assert s.p3.status == True


def test_triggeredby_basic(sysloader):
    class mysys(System):
        s1 = UserBoolSensor()
        s2 = UserBoolSensor()
        s3 = UserIntSensor()
        p = Program(active_condition=Or(s1, s2),
                    on_update=If(TriggeredBy(s1), SetStatus(s3, 1))
                    )

    s = sysloader.new_system(mysys)
    assert s.p.actual_triggers == {s.s1, s.s2}
    assert s.p.actual_targets == {s.s3}
    s.s2.status = 1
    s.flush()
    assert s.s3.status == 0
    s.s1.status = 1
    s.flush()
    assert s.s3.status == 1


def test_triggeredby_start(sysloader):
    l = []

    def fnc():
        l.append(1)

    class mysys(System):
        start = UserBoolSensor(
            active_condition=Value('start'),
            on_activate=SetStatus('mplayer', 'jotain')
        )
        mplayer = UserStrSensor(active_condition=Value('mplayer'),
                                on_update=If(TriggeredBy('mplayer'), Func(fnc)))
    s = sysloader.new_system(mysys)
    assert not l
    s.start.status = 1
    s.flush()
    assert l


def test_triggeredby_start2(sysloader):
    l = []

    def fnc():
        l.append(1)
        return 12

    class mysys(System):
        radiodei = UserEventSensor(
            on_activate=SetStatus('mplayer', 'mms://mms.radiodei.fi/RadioDeiR2HF')
        )

        reset_mplayer = Empty()

        mplayer_pid = UserIntSensor()
        mplayer = UserStrSensor(
            active_condition=Value('mplayer'),
            on_update=If(TriggeredBy('mplayer'),
                         Run(reset_mplayer),
                         SetStatus(mplayer_pid,
                                   Func(fnc))),
        )
    s = sysloader.new_system(mysys)
    assert not l
    s.radiodei.status = 1
    s.flush()
    assert l
    assert s.mplayer_pid.status == 12


def test_triggeredby_list(sysloader):
    class mysys(System):
        s1 = UserBoolSensor()
        s2 = UserBoolSensor()
        s3 = UserBoolSensor()
        s4 = UserBoolSensor()
        a = UserIntSensor()
        p = Program(active_condition=Or(s1, s2, s3, s4),
                    on_update=If(TriggeredBy(s1, s2), SetStatus(a, 1))
                    )

    s = sysloader.new_system(mysys)
    assert s.p.actual_triggers == {s.s1, s.s2, s.s3, s.s4}
    assert s.p.actual_targets == {s.a}
    s.s3.status = 1
    s.flush()
    assert s.a.status == 0
    s.s4.status = 1
    s.flush()
    assert s.a.status == 0
    s.s1.status = 1
    s.flush()
    assert s.a.status == 1


def test_triggeredby_triggername(sysloader):
    class mysys(System):
        s1 = UserBoolSensor()
        s2 = UserBoolSensor()
        s3 = UserBoolSensor()
        s4 = UserBoolSensor()
        a = UserIntSensor()
        p = Program(active_condition=Or(s1, s2, s3, s4),
                    on_update=If(Equal(TriggeredBy(), s1), SetStatus(a, 1))
                    )

    s = sysloader.new_system(mysys)
    assert s.p.actual_triggers == {s.s1, s.s2, s.s3, s.s4}
    assert s.p.actual_targets == {s.a}
    s.s3.status = 1
    s.flush()
    assert s.a.status == 0
    s.s4.status = 1
    s.flush()
    assert s.a.status == 0
    s.s1.status = 1
    s.flush()
    assert s.a.status == 1
