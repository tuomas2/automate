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
from automate.statusobject import AbstractSensor, AbstractActuator

import time


def test_namespace():
    sys = System(exclude_services=['TextUIService'])
    ns = sys.namespace  # AutomateNamespace(sys)
    # ns.set_system()
    s = AbstractSensor()

    ns['sens'] = s
    assert s in ns.reverse
    assert 'sens' in ns
    #assert ns.sens is s
    assert s in sys.sensors

    ns['one'] = 1
    assert 1 not in ns.reverse

    a = AbstractActuator()
    ns['act'] = a
    with pytest.raises(ValueError):
        ns['act'] = a

    assert a in sys.actuators
    assert a not in sys.sensors

    p = Program()
    ns['prg'] = p
    assert p in sys.programs
    #assert 'sensors' in ns
    #assert 'programs' in ns
    #assert 'actuators' in ns
    del ns['prg']
    assert not p in sys.programs
    del ns['act']
    assert not a in sys.actuators
    sys.cleanup()


@pytest.yield_fixture(params=[0, 1])
def mysys(request):
    class sysclass(System):
        mysensor = UserFloatSensor()
        myactuator = FloatActuator()
        prog = Program(active_condition=Value(mysensor if request.param else 'mysensor'),
                       on_update=Run(
                           SetStatus(myactuator if request.param else 'myactuator', 1),
                           Debug("Hello World!")),
                       )
    s = sysclass(exclude_services=['TextUIService'])

    yield s
    s.cleanup()


def test_tags(mysys):
    mysys.mysensor.tags = ['hep', 'hop']
    assert mysys.mysensor.tags == {'hep', 'hop'}
    mysys.mysensor.tags = 'hup,hip'
    assert mysys.mysensor.tags == {'hup', 'hip'}

    #['hep', 'hop']


def test_logging(caplog, mysys):
    out = caplog.text()
    s = 'Initializing services'
    assert s in out
    out = out.replace(s, '')
    assert s not in out


def test_automatesystem(mysys):
    s = mysys
    assert s.mysensor.status == False
    assert s.myactuator.status == False
    s.mysensor.set_status(1)
    s.flush()
    assert s.myactuator.status == True
    ns = s.namespace


def test_register_function(mysys):
    def func():
        return True
    mysys.register_service_functions(func)
    assert mysys.namespace['func']()
    assert mysys.func()

    class tst(object):

        def hep(self):
            return self.status
    t = tst()
    t.status = True
    mysys.register_service_functions(t.hep)
    assert mysys.hep()


def test_namechange(mysys):
    assert mysys.mysensor.name == 'mysensor'
    mysys.mysensor.name = 'newname'
    assert mysys.mysensor.name == 'newname'
    assert 'newname' in mysys.namespace
    assert 'mysensor' not in mysys.namespace


def test_new_systemobj(mysys):
    a1 = FloatActuator('somename', system=mysys)
    assert 'somename' in mysys.namespace
    mysys.prog.on_update = Run(SetStatus(mysys.myactuator, 1), SetStatus(a1, 2.0))
    mysys.mysensor.set_status(1)
    mysys.flush()
    assert a1.status == 2.0
    a2 = FloatActuator('somename', system=mysys)
    assert a2.name == 'somename_00'
    a3 = FloatActuator('somename', system=mysys)
    assert a3.name == 'somename_01'
    a4 = FloatActuator(system=mysys)
    assert a4.name == 'Nameless_FloatActuator'

from automate.common import Lock


def test_lock(sysloader):
    class mysys(System):
        prg = UserIntSensor()
    s = sysloader.new_system(mysys)

    l = Lock('name')
    flag = []

    def locktst():
        assert l.context
        l.release()
        flag.append(1)
    c = s.prg.on_deactivate = Delay(0.2, Func(locktst))
    c.call(s.prg)
    l.acquire()
    # now l is locked, but locktst will release it.
    l.acquire() # This will wait until l is released.

    assert flag
    l.release() # final release.


def test_sysobject_callable(sysloader):
    class mysys(System):
        mysens = UserIntSensor(on_activate=Run('mycal'), priority=50)
        mycal = Run(Run(Value(1), Shell('false')), Value(2))
    s = sysloader.new_system(mysys)


def test_sysobject_callable2(sysloader):
    class mysys(System):
        mysens = UserIntSensor(on_activate=Run('mycal'), priority=50)
        mycal = SetStatus('mysens', Add(Value('mysens'), 1))
    s = sysloader.new_system(mysys)

# test some Sensors


def test_shellsensor_defaultfilter(sysloader):
    class mysys(System):
        p1 = ShellSensor(cmd='echo test\necho test2\necho test3')
    s = sysloader.new_system(mysys)
    time.sleep(0.1)
    assert s.p1.status == 'test3\n'


def test_shellsensor_defaultfilter_simple(sysloader):
    class mysys(System):
        p1 = ShellSensor(cmd='echo test\necho test2\necho test3')
    s = sysloader.new_system(mysys)
    time.sleep(0.1)
    assert s.p1.status == 'test3\n'


def test_shellsensor_simple(sysloader):
    lines = []

    def myfunc(line):
        lines.append(line)
        return line[:-1]

    class mysys(System):
        p1 = ShellSensor(cmd='echo test\necho test2\necho test3', filter=myfunc)
    s = sysloader.new_system(mysys)
    time.sleep(0.1)
    assert s.p1.status == 'test3'
    assert lines == ['test line', 'test\n', 'test2\n', 'test3\n']


def test_shellsensor(sysloader):
    lines = []

    def myfunc(q):
        while True:
            line = q.get()
            if not line:
                break
            lines.append(line)
            yield line[:-1]

    class mysys(System):
        p1 = ShellSensor(cmd='echo test\necho test2\necho test3', filter=myfunc)
    s = sysloader.new_system(mysys)
    time.sleep(0.1)
    assert s.p1.status == 'test3'
    assert lines == ['test\n', 'test2\n', 'test3\n']


def test_shellsensor_delayed(sysloader):
    lines = []

    def myfunc(q):
        while True:
            line = q.get()
            if not line:
                break
            lines.append(line)
            yield line[:-1]

    class mysys(System):
        p1 = ShellSensor(cmd='echo;echo test\necho test2\necho\n\n\nsleep 0.1\necho test3', filter=myfunc)
    s = sysloader.new_system(mysys)
    time.sleep(1)
    assert s.p1.status == 'test3'
    assert lines == ['\n', 'test\n', 'test2\n', '\n', 'test3\n']


def test_setup_system(sysloader):
    class mysys(System):
        lamppu1 = BoolActuator()
        lamppu2 = BoolActuator()
        lamppu3 = BoolActuator()
        lamp_on_delay = UserFloatSensor()
        lamp_off_delay = UserFloatSensor()

        lamput = BoolActuator(
            active_condition=Value(True),
            on_update=Run(
                SetStatus(lamppu1, 'lamput'),
                Delay(IfElse('lamput', lamp_on_delay, lamp_off_delay),
                      SetStatus(lamppu3, 'lamput')),
                Delay(IfElse('lamput', Value(2) * lamp_on_delay, Value(2) * lamp_off_delay),
                      If(Not('lamput'),
                         Empty(),  # RemoteFunc(raspi2host, 'set_status', 'akvadimmer', 1)
                         ),
                      Delay(5,
                            SetStatus(lamppu2, 'lamput')),
                      )),
        )
    s = sysloader.new_system(mysys)
    a = s.lamput.on_update
    assert a.system  # run
    assert a[0].system  # setstatus
    assert a[1].system  # delay
    assert a[1][0].system  # ifelse
    assert a[1][1].system  # setstatus
    assert a[2].system  # delay
    assert a[2][0].system  # ifelse
    assert a[2][0][1].system  # mult
    assert a[2][0][1][0].system  # value
    assert a[2][0][2].system  # mult
    assert a[2][0][2][0].system  # value

#@mock.patch('traits_enaml.imports')
#@mock.patch('enaml.qt')
# def test_guithread(mock_qt, mock_traits):
#    g = GuiThread()
#    g.start()
#    g.stop = True
#    g.trigger()
