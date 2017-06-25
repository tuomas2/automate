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
import lamps

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

        testpin = ArduinoDigitalActuator(dev=0, pin=13, default=False)
        testpin_toggle = UserBoolSensor(on_update=SetStatus('testpin', 'testpin_toggle'))

    class Lirc(Group):
        lirc_sensor = ShellSensor(cmd='irw', filter=lirc_filter, default='', reset_delay=1.3,
                                  active_condition=Value('lirc_sensor'),
                                  on_update=Switch('lirc_sensor',
                                                   {'KEY_1': SetStatus('preset1', Not('preset1')),
                                                    'KEY_2': SetStatus('preset2', Not('preset2')),
                                                    'KEY_3': SetStatus('preset3', Not('preset3')),
                                                    }
                                                   ),
                                  )

    Lamps = lamps.get_lamps_group()


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
