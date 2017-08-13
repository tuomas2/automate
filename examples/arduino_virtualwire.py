from logging.config import dictConfig
import pyfirmata

from automate.extensions.arduino import arduino_service
from automate.extensions.arduino.arduino_actuators import ArduinoRemoteDigitalActuator, \
    ArduinoRemotePWMActuator

from automate.extensions.arduino.arduino_sensors import (
    ArduinoRemoteDigitalSensor,   ArduinoDigitalSensor, ArduinoAnalogSensor,  ArduinoRemoteAnalogSensor)

from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService
from automate.extensions.arduino.arduino_callables import VirtualWireCommand, \
    FirmataCommand
from automate.extensions.webui import WebService



LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'colorful': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(asctime)s %(log_color)s%(name)s%(reset)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            # 'formatter': 'verbose',
            'formatter': 'colorful',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'traits': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'automate.arduino_virtualwire.ArduinoService': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
         'django.template': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
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


source_home = target_home = 0
source_dev = 0
target_dev = 4


class ArduinoSystem(System):
    class Input(Group):
        reset1 = UserEventSensor(
            on_activate=FirmataCommand(0, pyfirmata.SYSTEM_RESET)
        )
        reset2 = UserEventSensor(
            on_activate=FirmataCommand(1, pyfirmata.SYSTEM_RESET)
        )
        #inputmode = UserEventSensor(
        #    on_activate=FirmataCommand(1, pyfirmata.SET_PIN_MODE, 10, pyfirmata.INPUT)
        #)

        ustr0 = UserStrSensor()
        ustr1 = UserStrSensor()
        remote_actuator_set = UserBoolSensor()
        remote_pwm_set = UserFloatSensor(value_min=0, value_max=1)

        target13 = UserBoolSensor(
            on_update=VirtualWireCommand(0, target_dev,
                                         arduino_service.VIRTUALWIRE_SET_DIGITAL_PIN_VALUE, 13,
                                         'target13')
        )

        local_pwm_set = UserFloatSensor(value_min=0, value_max=1)

    class Local(Group):
        local_pwm = ArduinoPWMActuator(service=1, pin=11, on_update=SetStatus('local_pwm', 'local_pwm_set'))
        local_pwm1 = ArduinoPWMActuator(service=0, pin=3, on_update=SetStatus('local_pwm1', 'local_pwm_set'))

        remote_actuator = ArduinoRemoteDigitalActuator(
            service=0, device=target_dev, pin=13,
            on_update=SetStatus('remote_actuator', 'remote_actuator_set'))

        remote_pwm = ArduinoRemotePWMActuator(service=0, device=target_dev, pin=3,
                                              on_update=SetStatus('remote_pwm', 'remote_pwm_set'))

        source_sens1 = ArduinoDigitalSensor(service=0, pull_up_resistor=True, pin=2)
        source_sens1_2 = ArduinoDigitalSensor(service=1, pull_up_resistor=True, pin=2)
        source_sens2 = ArduinoAnalogSensor(service=0, pin=0)

    class Remote(Group):
        awds1 = ArduinoRemoteDigitalSensor(service=1, device=source_dev, pin=2) # receives via VW
        awds2 = ArduinoRemoteAnalogSensor(service=1, device=source_dev, pin=0) # receives via VW


vw_speed = 7
s = ArduinoSystem(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=8000,
            home_address=source_home,
            device_address=source_dev,
            #virtualwire_ptt_pin=9,
            virtualwire_tx_pin=11,
            keep_alive=True,
            wakeup_pin=2,
            virtualwire_speed=vw_speed,
        ),
        ArduinoService(
            device="/dev/ttyUSB1",
            sample_rate=8000,
            home_address=target_home,
            device_address=target_dev,
            virtualwire_rx_pin=10,
            virtualwire_speed=vw_speed,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
