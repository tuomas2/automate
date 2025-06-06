#!/usr/bin/env python
# encoding: utf-8
""" A more advanced example program implementing some aquarium automatization
  Read through and try to understand. Some helpful comments inside.

  A more through tutorial is on my TODO list.
"""

import automate
import commonmixin
from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, \
    ArduinoDigitalSensor, ArduinoAnalogSensor, ArduinoService
from automate.extensions.arduino import ArduinoPWMActuator
from automate.extensions.rpc import RpcService
from automate.extensions.rpio import RpioSensor, TemperatureSensor, RpioActuator
from automate.extensions.webui import WebService
from automate.program import Program
from automate.statusobject import AbstractActuator
import time

import socket

one_hour = 60 * 60 * 1

socket.setdefaulttimeout(30) # Do not keep waiting forever for RemoteFuncs

def is_raspi():
    """Only in my raspi1,2 computers enable GPIO"""
    import platform
    return platform.node() in ["raspi1", "raspi2"]


def read_cpu_temp(caller):
    fname = "/sys/class/thermal/thermal_zone0/temp"
    with open(fname) as f:
        try:
            temp = float(f.read()) / 1000.
        except IOError:
            caller.logger.error("IO-error in temperature sensor %s, not set", caller.name)
            return
    return temp

import spotprice

excluded_hours = [7,8,9,19,20,21]

def spot_price():
    price = spotprice.get_current_spot_price(excluded_hours)
    if price is None:
        price = 100
    return price

def spot_threshold():
    return spotprice.get_threshold_for_hours(3, excluded_hours)

# GPIO pin configuration
relays = [7, 8, 25, 24, 23, 18, 3, 2]

inputboard = [17, 27, 22, 10, 11, 14, 15,
              5, 6, 13, 19, 13, 20,  #new rpi3 pins
              ]

inputpins = [12, 16, 21]
outputpins = [9]

NOT_USED = None

portmap = {
    # inputs:
    'ylivalutus': inputboard[0],

    'ala_altaat_alaraja': inputpins[0],
    'pääallas yläraja uusi': inputpins[1],

    # outputs:
    'alarm': outputpins[0],

    #'uvc_filter': relays[0],
    'allpumps': relays[1],
    #'lamp3': relays[2], #lamppu3
    'kv_pumppu1': relays[2],
    'kv_pumppu2': relays[3],
    #'co2input': relays[3],
    'heater': relays[4],
    'led': relays[5],
    #'lamp2': relays[6],
    #'led': relays[7], # RIKKI! on oikeasti. Ledin kanssa alkoi temppuilemaan niin että sammuu itsestään hetken kuluttua.
}
# GPIO port 4 is reserved for temperature sensor
#bread = [17, 27, 22, 10, 9, 11, 2, 3]


akva = "28-3ce1d443276a" #uppo


raspi2host = 'http://raspi2:3031/' if is_raspi() else 'http://localhost:3031/'


def calc_ph(v4, v6, v):
    p6 = 6.86
    p4 = 4.00

    a = (p6-p4)/(v6-v4)
    b = p6 - v6*(p6-p4)/(v6-v4)
    return a*v + b


class IsRaspi(SystemObject, SortableMixin):

    def call(self, caller, **kwargs):
        return is_raspi()


class RelayActuator(RpioActuator):

    """ Actuator for setting inverted Raspberry PI GPIO port statuses (on/off)"""
    inverted = CBool(True)


class Aquarium(commonmixin.CommonMixin, System):
    israspi = IsRaspi()
    push_sender = PushOver(
        api_key=os.getenv('PUSHOVER_API_KEY'),
        user_key=os.getenv('PUSHOVER_USER_KEY'))

    push_sender_emergency = PushOver(
        api_key=os.getenv('PUSHOVER_API_KEY'),
        user_key=os.getenv('PUSHOVER_USER_KEY'),
        priority=2,
    )

    class Sensors(Group):
        ylivalutus = RpioSensor(port=portmap['ylivalutus'], change_delay=2,
                                description='Ylivalutuksen alla lattialla (suojalaatikon sisällä)',
                                )
        vetta_yli_altaan = RpioSensor(port=portmap['pääallas yläraja uusi'], change_delay=1, button_type="up")

        ala_altaat_alaraja = RpioSensor(
            port=portmap['ala_altaat_alaraja'],
            button_type='up',
            change_delay=1,
            inverted=True,
            active_condition=And(Not("vedenvaihtomoodi"), Value("ala_altaat_alaraja")),
            on_activate=Run('push_sender'),
            on_deactivate=Run('push_sender'),
        )

        water_temp_min = UserFloatSensor(default=24.8)
        water_temp_max = UserFloatSensor(default=30.5)
        aqua_temperature_triggered = UserBoolSensor(default=False, tags="quick,temperature")

        aqua_temperature = TemperatureSensor(
            tags='temperature,analog,quick',
            addr=akva,
            interval=60,
            default=28.1, # We should not add any more heat if sensor is broken!
            max_jump=2.,
            max_errors=7,
            active_condition=Or(Value('aqua_temperature') > water_temp_max,
                                Value('aqua_temperature') < water_temp_min,
                                Value('aqua_temperature_triggered')
                                ),
            on_activate=Run(SetStatus('aqua_temperature_triggered', 1), 'push_sender'),
            history_length=5000,
        )

        water_temp_adj = UserFloatSensor(tags="temperature", default=27.5)

        lammitin_prog = Program(
            tags="temperature",
            active_condition=Value(True),
            on_update=SetStatus(
                'lammitin',
                And(
                    Or(Value("lammitin_force"), Value('spot_cheap')),
                    Value('pumput'), # Don't heat if pumps are off
                    Value('aqua_temperature') < water_temp_adj)
            )
        )
        lammitin_force = UserBoolSensor(
            tags = "quick",
            on_update=Delay(5*one_hour, SetStatus("lammitin_force", 0)),
            triggers= ['lammitin_force']
        )

        cpu_lampo = PollingSensor(
            tags='temperature,analog',
            interval=5,
            history_length=1000,
            status_updater=Func(read_cpu_temp, add_caller=True),
            active_condition=Value('cpu_lampo') > 70,
            on_activate=Run(
                SetStatus('alarmtrigger', 1),
                Run('push_sender')),
            on_deactivate=Run('push_sender'),
            priority=2,
        )
        spot_price = PollingSensor(
            tags='electricity,temperature',
            interval=5,
            history_length=1000,
            status_updater=Func(spot_price),
        )
        spot_price_limit = PollingSensor(
            tags='electricity,temperature',
            interval=5,
            history_length=1000,
            status_updater=Func(spot_threshold),
        )
        spot_cheap = BoolActuator(
            tags='electricity,temperature',
            active_condition=Value(True),
            on_update=SetStatus("spot_cheap", Or(spot_price<spot_price_limit, Equal(spot_price, spot_price_limit))),
        )
    class Kytkimet(Group):
        vesivahinko_kytkin = UserBoolSensor(
            default=0,
            tags="quick",
            active_condition=Value('vesivahinko_kytkin'),
            on_deactivate=SetStatus('silence_alarm', 0),
        )

        led_manuaalimoodi = UserBoolSensor(
            default=0,
            tags="quick",
            active_condition=Value('led_manuaalimoodi'),
            on_update=SetStatus('led', 'led_kytkin'),
            priority=3
        )

        led_kytkin = UserBoolSensor(default=0, tags='quick')


        lomamoodi = UserBoolSensor(default=True)

        tstacts_disable = OfType(AbstractActuator, exclude=['alarm', 'alarmtrigger'])

        testimoodi = UserBoolSensor(
            default=0,
            hide_in_uml=True,
            active_condition=Value('testimoodi'),
            on_activate=Run(SetStatus(tstacts_disable, tstacts_disable),
                            #muistutuspiippi minuutin välein
                            While('testimoodi',
                                  Func(time.sleep, 60),
                                  SetStatus('alarmtrigger', 1),
                                  Func(time.sleep, 2),
                                  SetStatus('alarmtrigger', 0)
                                  )
                            ),
            update_condition=Or(OfType(RpioSensor, ArduinoDigitalSensor)),
            on_update=Run(
                SetStatus('alarmtrigger', 1), Delay(2, SetStatus('alarmtrigger', 0))),
            priority=10,
            tags='quick',
        )

        reload_arduino = UserEventSensor(
            on_activate=ReloadService('ArduinoService'),
        )

        kv_manual_mode = UserBoolSensor(
            active_condition=Value('kv_manual_mode'),
            on_activate=Run(
                SetStatus("kv_pumppu1", 1),
                SetStatus("kv_pumppu2", 1),
            ),
            priority=3,
            default=False,
            tags="quick",
        )
        kv_pause_switch = UserBoolSensor(
            active_condition=Value("kv_pause_switch"),
            on_activate=Run(
                SetStatus("kv_pumppu1", 0),
                SetStatus("kv_pumppu2", 0),
                Delay(3*one_hour, Run(
                    SetStatus("kv_pumppu1", 1),
                    SetStatus("kv_pumppu2", 1),
                    SetStatus("kv_pause_switch", 0)
                ))),
            priority = 4,
            default = False,
            tags="quick"
        )

    class Vesiaktuaattorit(Group):
        pumput = RelayActuator(
            port=portmap['allpumps'],
            default=1,
            safety_delay=30,
            safety_mode="rising")

        kv_pumppu1 = RelayActuator(
            port=portmap['kv_pumppu1'],
            default=1,
            safety_delay=5,
            safety_mode="rising")

        kv_pumppu2 = RelayActuator(
            port=portmap['kv_pumppu2'],
            default=1,
            safety_delay=5,
            safety_mode="rising")

        lammitin = RelayActuator(
            tags="temperature",
            port=portmap['heater'],
            default=0,
            safety_delay=60 * 3,
            safety_mode="both")

    class Lamppuryhma(Group):
        led = RelayActuator(
            port=portmap['led'],
            active_condition=Value(True),
            on_update = SetStatus("led_pwm", IfElse(Value("led"), Value("led_day"), Value("led_night"))),
            triggers = ["led"]
        )

        led_day = UserFloatSensor(value_min=0., value_max=1., default=1.)
        led_night = UserFloatSensor(value_min=0., value_max=1., default=0.01)

        led_pwm = ArduinoPWMActuator(service=0, pin=11, default=0., history_length=1000)

    class Ajastimet(Group):
        led_ajastin = CronTimerSensor(
            timer_on="0 7 * * *",
            timer_off="0 22 * * *",
            active_condition=Value(True),
            on_update=SetStatus('led', Value("led_ajastin")),
        )

    # Pump 1: On during day (10:00-18:00) and on odd nights (22:00-07:00)
    kv_pumppu1_ajastin = CronTimerSensor(
        timer_on="0 10 * * *; 0 22 1-31/2 * *",  # Turn on at 10:00 every day AND at 22:00 on odd days
        timer_off="0 19 * * *; 0 7 * * *",       # Turn off at 18:00 AND 07:00 every day
        active_condition=Value(True),
        on_update=SetStatus('kv_pumppu1', "kv_pumppu1_ajastin"),
        priority=2,
    )

    # Pump 2: On during day (10:00-18:00) and on even nights (22:00-07:00)
    kv_pumppu2_ajastin = CronTimerSensor(
        timer_on="0 10 * * *; 0 22 2-30/2 * *",  # Turn on at 10:00 every day AND at 22:00 on even days
        timer_off="0 19 * * *; 0 7 * * *",       # Turn off at 18:00 AND 07:00 every day
        active_condition=Value(True),
        on_update=SetStatus('kv_pumppu2', "kv_pumppu2_ajastin"),
        priority=2,
    )

    class Alarm(Group):
        alarminterval = IntervalTimerSensor(interval=0.5, poll_active=False)

        silence_alarm = UserBoolSensor(
            active_condition=Value('silence_alarm'),
            on_activate=SetStatus('alarm', False),
            priority=6,
        )
        if is_raspi():
            alarm = RpioActuator(port=portmap['alarm'], default=False, silent=True)
        else:
            alarm = ArduinoDigitalActuator(service=0, pin=13, default=False, silent=True,
                                            active_condition=Value('alarm'),
                                            on_activate=Shell("notify.sh", no_wait=True)
            )

        alarmtrigger = BoolActuator(
            active_condition=Value('alarmtrigger'),
            on_update=SetStatus('alarm', Product(0.5, 'alarminterval')),
            on_activate=SetAttr('alarminterval', poll_active=True),
            on_deactivate=Run(
                SetStatus('alarm', False), SetAttr('alarminterval', poll_active=False))
        )

    class Vesiohjelmat(Group):
        vesivahinko_ohjelma = Program(
            active_condition=And(Or(
                'ylivalutus',
                'vetta_yli_altaan',
                'vesivahinko_kytkin'
            ),
                Not('testimoodi'),
                Not('vedenvaihtomoodi')
            ),
            on_activate=Run(
                SetStatus('vesivahinko_kytkin', 1),
                SetStatus('pumput', 0),
                SetStatus('kv_pumppu1', 0),
                SetStatus('kv_pumppu2', 0),
                SetStatus('lammitin', 0),
                SetStatus('alarmtrigger', 1),
                Run('push_sender_emergency')),
            on_deactivate=Run('push_sender'),
            priority=5,
        )

        vedenvaihtomoodi = UserBoolSensor('vedenvaihtomoodi',
            active_condition=Value('vedenvaihtomoodi'),
            # on_activate=SetStatus('kv_pumppu', 0),
            priority=5,
            tags='quick'
        )
        # Jos kytkin laitetaan pois päältä, salli se vain jos alarajasensori on false myös.
        alaraja_saavutettu = UserBoolSensor(
            'alaraja_saavutettu',
            on_update=SetStatus("alaraja_saavutettu", IfElse("ala_altaat_alaraja", 1, "alaraja_saavutettu")),
            default=True,
        )

        waterchange1 = Program(
            active_condition=And('vedenvaihtomoodi', Or('alaraja_saavutettu', 'ala_altaat_alaraja')),
            on_activate=Run(
                SetStatus('pumput', 0),
                SetStatus('alaraja_saavutettu', 1),
                'push_sender'),
            priority=5,
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
                'release': automate.__version__,
                'dsn': RAVEN_DSN,
                'tags': {'automate-system': 'Aquarium'}
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
                'propagate': False,
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
            'traits': {
                'handlers': ['console', 'sentry'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }

    dictConfig(LOGGING)



    webcam_page = """
    {% extends "base.html" %}
    {%block content %}
    <img class='puml' src="/webcam/webcam.jpeg">
    {%endblock%}
    """

    web = WebService(
            server_url=os.getenv('AUTOAQUA_URL', 'http://localhost:8080'),
            http_port=8080,
            http_auth=(os.getenv('AUTOMATE_USERNAME', 'test'),
                       os.getenv('AUTOMATE_PASSWORD', 'test'),
            ),
            debug = not is_raspi(),
            user_tags={'quick'},
            read_only = False,
            default_view = 'tags_view',
            static_dirs = {'/webcam/(.*)': 'public_html/webcam/'},
            custom_pages = {'Webcam': webcam_page},
            django_settings = {'SESSION_FILE_PATH': 'sessions' if is_raspi() else '/tmp',
                               'SESSION_COOKIE_AGE': 52560000,
                               'SECRET_KEY': os.getenv('AUTOMATE_SECRET_KEY', 'unsecure-default'),
                               },
        )

    rpcs = RpcService(
        http_port=3030,
        view_tags={'quick'},
    )


    s = Aquarium.load_or_create(
        filename='aquarium.dmp',
        services=[
            web,
            rpcs,
            StatusSaverService(),
        ],
        no_input=not is_raspi(),
        raven_dsn=RAVEN_DSN,
    )

