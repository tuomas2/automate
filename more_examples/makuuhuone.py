# encoding:utf-8
from __future__ import unicode_literals
import automate
from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator
from automate.extensions.rpio import RpioSensor, RpioActuator
from automate.extensions.webui import WebService

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

raspi2host = 'http://raspi2:3031/'

class Makuuhuone(lamps.LampGroupsMixin, System):
    tmp_lamp_out = RpioActuator(port=2, default=0, active_condition=Value('preset1'), on_activate=SetStatus('tmp_lamp_out', 1))
    class RpioButtons(Group):
        button1 = RpioSensor(port=14, button_type='up', active_condition=Value('button1'), on_activate=Run('_toggler'))
        button2 = RpioSensor(port=15, button_type='up', active_condition=Value('button2'), on_activate=SetStatus('switch_off', 1))
        button3 = RpioSensor(port=18, button_type='up', active_condition=Value('button3'))

    class Lirc(Group):
        lirc_sensor = ShellSensor(
            cmd='irw', filter=lirc_filter, default='', reset_delay=0.5,
            exclude_triggers={'preset1', 'preset2', 'preset3', 'switch_off'},
            triggers={'lirc_sensor'},
            active_condition=Value(True),
            on_update=Switch(
                'lirc_sensor',
                {'KEY_1': SetStatus('preset1', Not('preset1')),
                 'KEY_2': SetStatus('preset2', Not('preset2')),
                 'KEY_3': SetStatus('preset3', Not('preset3')),
                 'KEY_MUTE': RemoteFunc(raspi2host, 'set_status', 'pause', 1),
                 'KEY_A': RemoteFunc(raspi2host, 'set_status', 'next', 1),
                 'KEY_SCALE': RemoteFunc(raspi2host, 'set_status', 'prev', 1),
                 'KEY_VOLUMEUP': RemoteFunc(raspi2host, 'set_status', 'volume_pcm_only',
                                            RemoteFunc(raspi2host, 'get_status', 'volume_pcm_only') + 1),
                 'KEY_VOLUMEDOWN': RemoteFunc(raspi2host, 'set_status', 'volume_pcm_only',
                                              RemoteFunc(raspi2host, 'get_status', 'volume_pcm_only') - 1),
                 'KEY_CHANNELUP': RemoteFunc(raspi2host, 'set_status', 'mpc_instance',
                                            RemoteFunc(raspi2host, 'get_status', 'mpc_instance') + 1),
                 'KEY_CHANNELDOWN': RemoteFunc(raspi2host, 'set_status', 'mpc_instance',
                                              RemoteFunc(raspi2host, 'get_status', 'mpc_instance') - 1),
                 'KEY_POWER': SetStatus('switch_off', Value(True)),
                 }
            ),
        )

    class SystemInfo(Group):
        tags = 'web'
        load_average = PollingSensor(interval=10, status_updater=ToStr('{}', Func(os.getloadavg)))
        memory = PollingSensor(interval=10, status_updater=ToStr(Func(meminfo)))

    class Debug(Group):
        tags = 'web'
        testpin = ArduinoDigitalActuator(pin=13, default=False)
        testpin_toggle = UserBoolSensor(on_update=SetStatus('testpin', 'testpin_toggle'))
        reload_arduino = UserEventSensor(
            on_activate=ReloadService('ArduinoService'),
        )


if __name__ == '__main__':
    from logging.config import dictConfig

    RAVEN_DSN = os.getenv('RAVEN_DSN', '')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(name)s %(message)s'
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
            'colorful': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(asctime)s %(log_color)s%(name)s%(reset)s %(message)s'
                # 'format': "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s"
            }
        },
        'handlers': {
            'sentry': {
                'level': 'ERROR',
                'class': 'raven.handlers.logging.SentryHandler',
                'dsn': RAVEN_DSN,
                'release': automate.__version__,
                'tags': {'automate-system': 'makuuhuone'}
            },
            'console': {
                'class': 'logging.StreamHandler',
                # 'formatter': 'verbose',
                'formatter': 'colorful',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console', 'sentry'],
                'level': 'INFO',
                'propagate': True,
            },
            'automate': {
                'handlers': ['console', 'sentry'],
                'level': 'INFO',
                'propagate': True,
            },
            'django.template': {
                'handlers': ['console', 'sentry'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django': {
                'handlers': ['console', 'sentry'],
                'level': 'INFO',
                'propagate': False,
            },
            'tornado.access': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
    }

    dictConfig(LOGGING)

    s = Makuuhuone.load_or_create(
        'makuuhuone.dmp',
        services=[
            WebService(
                server_url=os.getenv('MAKUUHUONE_URL', 'http://localhost:8080'),
                http_port=8080,
                http_auth=(os.getenv('AUTOMATE_USERNAME', 'test'),
                           os.getenv('AUTOMATE_PASSWORD', 'test')),
                debug=False if is_raspi() else True,
                user_tags={'web'}, default_view='user_defined_view',
                read_only=False,
                show_actuator_details=False,
                django_settings = {'SESSION_FILE_PATH': 'sessions' if is_raspi() else '/tmp',
                                   'SESSION_COOKIE_AGE': 52560000,
                                   'SECRET_KEY': os.getenv('AUTOMATE_SECRET_KEY', 'unsecure-default'),
                                   },
            ),
            StatusSaverService(),
        ],
        no_input=not is_raspi(),
        raven_dsn=RAVEN_DSN,
    )
