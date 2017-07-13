#!/usr/bin/env python
# encoding: utf-8
""" A more advanced example program implementing some aquarium automatization
  Read through and try to understand. Some helpful comments inside.

  A more through tutorial is on my TODO list.
"""
from __future__ import division
from __future__ import unicode_literals
from past.utils import old_div

from automate import *
from automate.extensions.arduino import ArduinoService, ArduinoDigitalActuator, \
    ArduinoDigitalSensor
from automate.extensions.rpc import RpcService
from automate.extensions.rpio import RpioSensor, TemperatureSensor, RpioActuator
from automate.extensions.webui import WebService
from automate.program import Program
from automate.statusobject import AbstractActuator
import time

import socket
socket.setdefaulttimeout(30) # Do not keep waiting forever for RemoteFuncs

def is_raspi():
    """Only in my raspi1,2 computers enable GPIO"""
    import platform
    return platform.node() in ["raspi1", "raspi2"]

def read_cpu_temp(caller):
    fname = "/sys/class/thermal/thermal_zone0/temp"
    f = open(fname)
    try:
        temp = old_div(float(f.read()), 1000.)
    except IOError:
        caller.logger.error("IO-error in temperature sensor %s, not set", caller.name)
        return
    f.close()
    return temp


# GPIO pin configuration
relays = [7, 8, 25, 24, 23, 18, 3, 2]

# inputboard_new = [17, 27, 22, 10, 11, 14, 15, a2,a3,a4,a5,a6,a7,a8]  # 9 on alarmille

inputboard = [17, 27, 22, 10, 11, 14, 15]  # 9 on alarmille
arduino_ports = {
    'kaapin sensori': 2,
    'ala varoitus': 3,
    'keski lattiasensori': 4,
    'unused4': 5,
    'unused5': 6,
    'unused6': 7,
    'alarm': 8,
    'co2_stop': 11,
}
portmap = {
    # inputs:
    'palkit': inputboard[0],
    'pääallas yläraja critical': inputboard[1],
    'pääallas yläraja warning': inputboard[2],
    'valutusputki': inputboard[3],
    'ala-altaiden alaraja': inputboard[4],
    'ala-altaiden yläraja': inputboard[5],  # ei vielä aktivoitu (--what -- kai nyt sentään on?)
    'vasen lattiasensori': inputboard[6],  # ei vielä aktivoitu

    # outputs:
    'alarm': 9,
    'uvc_filter': relays[0],
    'allpumps': relays[1],
    'NOT_YET_IN_USE': relays[2],
    'co2input': relays[3],
    'heater': relays[4],
    'lamp1': relays[5],
    'lamp2': relays[6],
    'lamp3': relays[7],
}
# GPIO port 4 is reserved for temperature sensor
#bread = [17, 27, 22, 10, 9, 11, 2, 3]

sisa = "28-000005502fec"
ulko = "28-0000055162f1"
akva = "28-00000558263c"

raspi2host = 'http://raspi2:3031/' if is_raspi() else 'http://localhost:3031/'


class IsRaspi(SystemObject):

    def call(self, caller, **kwargs):
        return is_raspi()


class RelayActuator(RpioActuator):

    """ Actuator for setting inverted Raspberry PI GPIO port statuses (on/off)"""
    inverted = CBool(True)


class autoaqua(System):
    israspi = IsRaspi()
    push_sender = PushOver(
        api_key=os.getenv('PUSHOVER_API_KEY'),
        user_key=os.getenv('PUSHOVER_USER_KEY'))

    raspi2_alive = PollingSensor(
        interval=10.,
        status_updater=RemoteFunc(raspi2host, 'is_alive'),
        active_condition=Value('raspi2_alive'),
        on_deactivate=If(israspi, push_sender),
    )

    # raspi2_cmd = UserAnySensor(
    #    on_update=RemoteFunc(raspi2host, 'set_status', Value('raspi2_cmd'), True)
    #)

    # raspi2_start = RPCActuator(
    #    slave=True,
    #    remote_sensor='start',
    #    host='http://raspi1:3031/' if is_raspi() else 'http://localhost:3031/',
    #)

    class Sensors(Group):
        valutusputki = RpioSensor(port=portmap['valutusputki'], change_delay=1)
        vetta_yli_altaan = RpioSensor(port=portmap['pääallas yläraja critical'], change_delay=1)
        palkit = RpioSensor(port=portmap['palkit'], change_delay=2)
        ala_altaat_ylaraja = RpioSensor(port=portmap['ala-altaiden yläraja'], change_delay=1)

        vetta_yli_altaan_warning = RpioSensor(port=portmap['pääallas yläraja warning'],
                                              change_delay=1,
                                              active_condition=And(Or(
                                                  'vetta_yli_altaan_warning',
                                                  # keittion_vesivahinko
                                              ),
            Not('testimoodi')),
            on_activate=Run('push_sender',
                            SetStatus('alarmtrigger', 1),
                            ),
            priority=4,
        )

        lattiasensori_1 = RpioSensor(port=portmap['vasen lattiasensori'], change_delay=1,
                                     description='Ylivalutuksen alla lattialla')

        ala_altaat_alaraja = RpioSensor(port=portmap['ala-altaiden alaraja'], change_delay=1,
                                        inverted=True)

        kaapin_ulkosuodatin = ArduinoDigitalSensor(dev=0, pin=arduino_ports['kaapin sensori'], change_delay=1)
        lattiasensori_2 = ArduinoDigitalSensor(dev=0, pin=arduino_ports['keski lattiasensori'], change_delay=1,
                                               description='altaan alla oleva lattiasensori')
        ala_varoitus = ArduinoDigitalSensor(dev=0, pin=arduino_ports['ala varoitus'], change_delay=1)
        co2_stop_sensor = ArduinoDigitalSensor(dev=0, pin=arduino_ports['co2_stop'], safety_delay=800,
                                               safety_mode='falling', change_delay=1)
        #analog1 = ArduinoAnalogSensor(dev=0, pin=0, silent=True)

        water_temp_min = UserFloatSensor(default=20.0)
        water_temp_max = UserFloatSensor(default=30.5)

        aqua_temperature = TemperatureSensor(
            addr=akva,
            interval=60,
            default=25.123,
            max_jump=2.,
            max_errors=7,
            active_condition=Or(Value('aqua_temperature') > water_temp_max, Value('aqua_temperature') < water_temp_min),
            on_activate=Run('push_sender'),
        )

        parvekkeen_lampo = TemperatureSensor(addr=ulko, interval=60, default=25.123)

        cpu_lampo = PollingSensor(
            interval=5,
            status_updater=Func(read_cpu_temp, add_caller=True),
            active_condition=Value('cpu_lampo') > 70,
            on_activate=Run(
                SetStatus('alarmtrigger', 1),
                Run('push_sender')),
            priority=2
        )

        ph = UserFloatSensor(default=6.5)
        sahkot = UserBoolSensor(default=1,
                                active_condition=Not('sahkot'),
                                on_activate=Run(SetStatus('lamppu1', 0), SetStatus('lamppu2', 0), SetStatus('lamppu3', 0),
                                                Delay(5 * 60,
                                                      Run(SetStatus('pumput', 0), SetStatus('co2', 0))),
                                                'push_sender'),
                                priority=4,
                                )

    class Kytkimet(Group):
        vesivahinko_kytkin = UserBoolSensor(default=0, tags="switch,web",
                                            active_condition=Value('vesivahinko_kytkin'),
                                            on_deactivate=SetStatus('silence_alarm', 0),
                                           )
        valot_manuaalimoodi = UserBoolSensor(default=1,
                                             tags="switch,web,quick",
                                             active_condition=Value('valot_manuaalimoodi'),
                                             on_update=SetStatus('lamput', 'valot_kytkin'),
                                             priority=3
                                             )

        valot_kytkin = UserBoolSensor(default=0, tags='quick')
        lomamoodi = UserBoolSensor(default=0, tags="switch,web")

        tstacts_disable = OfType(AbstractActuator, exclude=['alarm', 'alarmtrigger'])

        testimoodi = UserBoolSensor(default=0,
                                    hide_in_uml=True,
                                    tags="switch,web,quick",
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
                                    )

        vedenvaihtomoodi = UserBoolSensor(default=0, tags="switch,web,quick")
        co2_stop = UserBoolSensor(default=False,
                                  active_condition=Or(Not('pumput'), 'co2_stop', 'co2_stop_sensor'),
                                  priority=5,
                                  on_activate=SetStatus('co2', False))

        co2_force_on = UserBoolSensor(default=False,
                                  active_condition=Value('co2_force_on'),
                                  priority=4,
                                  on_activate=SetStatus('co2', True))

        uvc_stop = UserBoolSensor(description='Stops UVC either manually or if pumps are down',
                                  default=False,
                                  active_condition=Or(Not('pumput'), 'uvc_stop'),
                                  priority=5,
                                  on_activate=SetStatus('uvc', False))

        uvc_force_on = UserBoolSensor(
                                  default=False,
                                  active_condition=And('pumput', 'uvc_force_on'),
                                  priority=4,
                                  on_activate=SetStatus('uvc', True))

        reload_arduino = UserEventSensor(
            on_activate=ReloadService('ArduinoService'),
        )

        lamput_ajastin1_k = UserBoolSensor(default=True)
        lamput_ajastin2_k = UserBoolSensor(default=False)

    class Vesiaktuaattorit(Group):
        uvc = RelayActuator(port=portmap['uvc_filter'], default=0, safety_delay=30)
        pumput = RelayActuator(port=portmap['allpumps'], default=1, safety_delay=30, safety_mode="rising")
        co2 = RelayActuator(port=portmap['co2input'],  default=0, safety_delay=60 * 2, safety_mode="rising")
        lammitin = RelayActuator(port=portmap['heater'],  default=1, safety_delay=60 * 3, safety_mode="both")

    class Lamppuryhma(Group):
        lamp_safety_delay = 30 * 60
        lamppu1 = RelayActuator(port=portmap['lamp1'], safety_delay=lamp_safety_delay, safety_mode="rising")
        lamppu2 = RelayActuator(port=portmap['lamp2'], safety_delay=lamp_safety_delay, safety_mode="rising")
        lamppu3 = RelayActuator(port=portmap['lamp3'], safety_delay=lamp_safety_delay, safety_mode="rising")

        lamp_on_delay = UserFloatSensor(default=2*60)
        lamp_off_delay = UserFloatSensor(default=2*60)


        lamput = BoolActuator(
            active_condition=Value('lamput_ajastin1_k'),
            on_update=Run(
                          SetStatus(lamppu1, 'lamput'),
                          Delay(IfElse('lamput', lamp_on_delay, lamp_off_delay),
                              SetStatus(lamppu3, 'lamput')),
                          Delay(IfElse('lamput', Value(2) * lamp_on_delay, Value(2) * lamp_off_delay),
                               #If(Not('lamput'),
                               #   RemoteFunc(raspi2host, 'set_status', 'akvadimmer', 1)
                               #   ),
                               #Delay(5,
                                   SetStatus(lamppu2, 'lamput')),
                               #)
                               ),
        )

        lamppu1_manual = UserBoolSensor(active_condition=Value('lamppu1_manual'),
                                        on_activate=SetStatus(lamppu1, 1),
                                        priority=2)
        lamppu2_manual = UserBoolSensor(active_condition=Value('lamppu2_manual'),
                                        on_activate=SetStatus(lamppu2, 1),
                                        priority=2, tags={'quick'})
        lamppu3_manual = UserBoolSensor(active_condition=Value('lamppu3_manual'),
                                        on_activate=SetStatus(lamppu3, 1),
                                        priority=2)

        switch_off_delay = UserFloatSensor(description='in minutes', default=15)

        switch_manual_lamps_off = UserBoolSensor(tags={'quick'},
            active_condition=Value('switch_manual_lamps_off'),
            on_activate=Delay(switch_off_delay*60,
                              SetStatus([lamppu1_manual,
                                         lamppu2_manual,
                                         lamppu3_manual,
                                         'switch_manual_lamps_off'],[0]*4))
        )

    class Ajastimet(Group):
        co2_ajastin = CronTimerSensor(timer_on="30 12 * * *",  # oli 5:30 mutta muutan turvallisemmaksi...
                                  timer_off="0 16 * * *")

        co2_ajastin_loma = CronTimerSensor(timer_on="30 15 * * *",
                                       timer_off="0 20 * * *",
                                       tags="holiday")

        # Muista: tämä kontrolloi (myös) UVC:ta!
        lamput_ajastin = CronTimerSensor(timer_on="0 14 * * *",
                                         timer_off="0 22 * * *")

        lamppu1_ajastin = CronTimerSensor(timer_on="0 13,15,18 * * *",
                                          timer_off="0 21 * * *;2 14,17 * * *",
                                          active_condition=And('lamput_ajastin2_k', 'lamppu1_ajastin'),
                                          on_activate=SetStatus('lamppu1', 1),
                                          )

        lamppu2_ajastin = CronTimerSensor(timer_on="2 13 * * *;0 16 * * *",
                                          timer_off="3 21 * * *;2 15 * * *",
                                          active_condition=And('lamput_ajastin2_k', 'lamppu2_ajastin'),
                                          on_activate=SetStatus('lamppu2', 1),
                                          )

        lamppu3_ajastin = CronTimerSensor(timer_on="0 14,17 * * *",
                                          timer_off="6 21 * * *;2 16 * * *",
                                          active_condition=And('lamput_ajastin2_k', 'lamppu3_ajastin'),
                                          on_activate=SetStatus('lamppu3', 1),
                                          )

        dimmer_ajastin = CronTimerSensor(timer_on="5 21 * * *",
                                         timer_off="10 21 * * *",
                                         active_condition=Value('dimmer_ajastin'),
                                         on_activate=If('lamput_ajastin2_k', Delay(50, RemoteFunc(raspi2host, 'set_status', 'akvadimmer', 1)))
                                         )

        #timer_on="0 10 * * mon-sat; 0 11 * * sun",
        # timer_off="30 20 * * mon-thu; 0 22 * * fri-sat,sun")

        lamput_ajastin_loma = CronTimerSensor(timer_on="0 16 * * *",
                                          timer_off="0 22 * * *",
                                          tags="holiday")

        ajastinohjelma = Program(on_update=IfElse('lomamoodi',
                                                  Run(SetStatus('lamput', lamput_ajastin_loma),
                                                      SetStatus(
                                                      'co2', co2_ajastin_loma),
                                                      Delay(30, SetStatus('uvc', lamput_ajastin_loma))),
                                                  Run(SetStatus('lamput', lamput_ajastin),
                                                      SetStatus('co2', co2_ajastin),
                                                      Delay(30, SetStatus('uvc', lamput_ajastin)))),
                                 priority=1.5,
                                 triggers = ['lomamoodi'],
                                 )

    class Alarm(Group):
        alarminterval = IntervalTimerSensor(interval=0.5, poll_active=False)

        silence_alarm = UserBoolSensor(
            active_condition=Value('silence_alarm'),
            on_activate=SetStatus('alarm', False),
            priority=6,
            tags='quick',
        )
        if is_raspi():
            alarm = ArduinoDigitalActuator(dev=0, pin=arduino_ports['alarm'], default=False, silent=True)
        else:
            alarm = ArduinoDigitalActuator(dev=0, pin=13, default=False, silent=True,
                                            active_condition=Value('alarm'),
                                            on_activate=Shell("notify.sh", no_wait=True)
            )

        alarmtrigger = BoolActuator(active_condition=Value('alarmtrigger'),
                                    on_update=SetStatus('alarm', Product(0.5, 'alarminterval')),
                                    on_activate=SetAttr('alarminterval', poll_active=True),
                                    on_deactivate=Run(
            SetStatus('alarm', False), SetAttr('alarminterval', poll_active=False))
        )

    class Vesiohjelmat(Group):
        vesivahinko_ohjelma = Program(active_condition=And(Or('valutusputki',
                                                              'ala_altaat_ylaraja',
                                                              'vetta_yli_altaan',
                                                              'palkit',
                                                              'lattiasensori_1',
                                                              'lattiasensori_2',
                                                              'vesivahinko_kytkin'),
                                                           Not('testimoodi')),
                                      on_activate=Run(
                                                      SetStatus('vesivahinko_kytkin', 1),
                                                      SetStatus('pumput', 0),
                                                      SetStatus('lammitin', 0),
                                                      SetStatus('alarmtrigger', 1),
                                                      Run('push_sender')),
                                                      priority=5,
        )

        alaraja_saavutettu = UserBoolSensor('alaraja_saavutettu', tags='web,quick')

        waterchange1 = Program(
            active_condition=And('vedenvaihtomoodi', Or('alaraja_saavutettu', 'ala_altaat_alaraja')),
            on_activate=Run(SetStatus('pumput', 0), SetStatus('alaraja_saavutettu', 1)),
            priority=5,
        )

        # TODO: yläraja on vähän huono. Parempi olisi sellainen "varoitussensori joka on alempana
        # kuin yläraja.
        waterchange2 = Program(active_condition=And('vedenvaihtomoodi', Or('ala_varoitus', 'ala_altaat_ylaraja')),
                               on_activate=Run(
                                   SetStatus('alarmtrigger', 1)),
                               )


webcam_page = """
{% extends "base.html" %}
{%block content %}
<img class='puml' src="/webcam/webcam.jpeg">
{%endblock%}
"""

import tornado.log
tornado.log.access_log.setLevel(logging.WARNING)

web = WebService(
        server_url=os.getenv('AUTOAQUA_URL', 'http://localhost:8080'),
        http_port=8080,
        http_auth=(os.getenv('AUTOMATE_USERNAME', 'test'),
                   os.getenv('AUTOMATE_PASSWORD', 'test'),
        ),
        debug = not is_raspi(),
        user_tags={'web'},
        read_only = False,
        default_view = 'tags_view',
        show_actuator_details = False,
        static_dirs = {'/webcam/(.*)': 'public_html/webcam/'},
        custom_pages = {'Webcam': webcam_page},
        django_settings = {'SESSION_FILE_PATH': 'sessions' if is_raspi() else '/tmp',
                           'SESSION_COOKIE_AGE': 52560000,
                           'SECRET_KEY': os.getenv('AUTOMATE_SECRET_KEY', 'unsecure-default')},
    )

ard = ArduinoService(
        arduino_devs=['/dev/ttyUSB0'],
        arduino_dev_types=['Arduino'],
        arduino_dev_sampling=[500],
    )
rpcs = RpcService(
        http_port=3030,
        view_tags={'web'},
    )


s = autoaqua.load_or_create(
    filename='akvadumppi.dmp',
    services=[
        web,
        ard,
        rpcs,
        PlantUMLService(url='http://www.plantuml.com/plantuml/svg/'),
        StatusSaverService(),
    ],
    print_level=logging.INFO,
    log_level=logging.INFO,
    logfile="autoaqua.log",
    no_input=not is_raspi(),
)
