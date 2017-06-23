# encoding:utf-8
from __future__ import unicode_literals
from automate import *
from automate.extensions.arduino import ArduinoPWMActuator, ArduinoDigitalActuator
from automate.extensions.webui import WebService
import time
import os
import psutil

import socket
socket.setdefaulttimeout(30) # Do not keep waiting forever for RemoteFuncs


def meminfo():
    return psutil.virtual_memory().percent


def is_raspi():
    """Only in my raspi1,2 computers enable GPIO"""
    import platform
    return platform.node() in ["raspi1", "raspi2", "raspi3"]


def lirc_filter(line):
    try:
        code, num, key, remote = line.split(' ')
    except ValueError:
        key = '-'
    print('Command ', key)
    return key


class Makuuhuone(System):
    class Commands(Group):
        tags = 'web'
        reload_arduino = UserEventSensor(
            on_activate=ReloadService('ArduinoService'),
        )
        reload_web = UserEventSensor(
            on_activate=ReloadService('WebService'),
        )

    class Lirc(Group):
        lirc_sensor = ShellSensor(cmd='irw', filter=lirc_filter, default='', reset_delay=1.3,
                                  active_condition=Value('lirc_sensor'),
                                  on_update=Switch('lirc_sensor',
                                                   {'KEY_1': SetStatus('preset1', 1),
                                                    'KEY_2': SetStatus('preset2', 1),
                                                    'KEY_3': SetStatus('preset3', 1),
                                                    }
                                                   ),
                                  )

    class Lamps(Group):
        testpin = ArduinoDigitalActuator(dev=0, pin=13, default=False)
        testpin_toggle = UserBoolSensor(on_update=SetStatus('testpin', 'testpin_toggle'))

        cold_lamp_out = ArduinoPWMActuator(dev=0, pin=5, default=0.)
        warm_lamp_out = ArduinoPWMActuator(dev=0, pin=9, default=0.)  # 9,10 30 kHz

        warm_preset1 = UserFloatSensor(value_min=0., value_max=1., default=.8)
        cold_preset1 = UserFloatSensor(value_min=0., value_max=1., default=.8)

        warm_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.4)
        cold_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.4)

        warm_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)
        cold_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)

        preset1 = UserBoolSensor(tags={'quick_lamps'},
                                 priority=2.,
                                 active_condition=Value('preset1'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset1'),
                                               SetStatus('cold_lamp_out', 'cold_preset1'),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset2 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset2'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset2'),
                                               SetStatus('cold_lamp_out', 'cold_preset2'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset3 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset3'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset3'),
                                               SetStatus('cold_lamp_out', 'cold_preset3'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                                ))

        switch_off = UserEventSensor(tags={'quick_lamps'}, on_activate=SetStatus(['fade_out', 'preset1', 'preset2', 'preset3'], [0]*4))

        fd_mpl = UserFloatSensor(description='multiplier', default=0.999, value_min=0.9, value_max=1.0)
        fd_thr = UserFloatSensor(description='threshold', default=0.001, value_min=0.0001, value_max=0.01)
        fd_slp = UserFloatSensor(description='sleep time', default=0.1, value_min=0.00, value_max=1.)

        dimmer = While(
                        Or(
                            Value('cold_lamp_out'),
                            Value('warm_lamp_out'),
                        ),
                        SetStatus('cold_lamp_out', IfElse(Value('cold_lamp_out') > Value(fd_thr),
                                                          Value('cold_lamp_out')*Value(fd_mpl), 0)),
                        SetStatus('warm_lamp_out', IfElse(Value('warm_lamp_out') > Value(fd_thr),
                                                          Value('warm_lamp_out')*Value(fd_mpl), 0)),
                        Func(time.sleep, 'fd_slp'),
                        do_after=Run(SetStatus(['preset1', 'preset2', 'preset3', 'fade_out', 'akvadimmer'], [0]*5))
                      )

        fade_out = UserBoolSensor(tags={'quick_lamps'}, priority=3,
                                     active_condition=Value('fade_out'),
                                     on_activate=Run('dimmer')
                                 )

    class SystemInfo(Group):
        load_average = PollingSensor(interval=10, status_updater=ToStr('{}', Func(os.getloadavg)))
        memory = PollingSensor(interval=10, status_updater=ToStr(Func(meminfo)))


import tornado.log
tornado.log.access_log.setLevel(logging.WARNING)

if __name__ == '__main__':
    s = Makuuhuone.load_or_create(
        'makuuhuone.dmp',
        services=[
            WebService(
                http_port=8080,
                http_auth=(os.getenv('AUTOMATE_USERNAME', 'test'),
                           os.getenv('AUTOMATE_PASSWORD', 'test')),
                debug=False if is_raspi() else True,
                user_tags={'web'}, default_view='user_defined_view',
                read_only=False,
                show_actuator_details=False,
                django_settings = {'SESSION_FILE_PATH': 'sessions' if is_raspi() else '/tmp',
                                   'SESSION_COOKIE_AGE': 52560000,
                                   'SECRET_KEY': os.getenv('AUTOMATE_SECRET_KEY', 'unsecure-default')},
            ),
            StatusSaverService(),
        ],
        logfile='makuuhuone.log' if is_raspi() else '',
        print_level=logging.INFO,
        log_level=logging.WARNING,
    )
