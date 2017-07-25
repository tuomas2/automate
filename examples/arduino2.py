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
        'automate.arduino2.ArduinoService': {
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
    ustr0 = UserStrSensor()
    ustr1 = UserStrSensor()
    ubool = UserBoolSensor()
    class Input(Group):
        reset1 = UserEventSensor(
            on_activate=FirmataCommand(0, pyfirmata.SYSTEM_RESET)
        )
        reset2 = UserEventSensor(
            on_activate=FirmataCommand(1, pyfirmata.SYSTEM_RESET)
        )

        ubool2 = UserBoolSensor(
            on_update=VirtualWireCommand(0, target_dev,
                                         arduino_service.VIRTUALWIRE_SET_DIGITAL_PIN_VALUE, 13,
                                         'ubool2')
        )

        ufloat1 = UserFloatSensor(value_min=0, value_max=1)
        ufloat2 = UserFloatSensor(value_min=0, value_max=1)

    class Local(Group):
        local_pwm = ArduinoPWMActuator(dev=0, pin=3, on_update=SetStatus('local_pwm', 'ufloat2'))

        remote_actuator = ArduinoRemoteDigitalActuator(dev=0, target_device=target_dev, target_pin=12,
                        on_update=SetStatus('remote_actuator', 'ubool'))

        remote_pwm = ArduinoRemotePWMActuator(dev=0, target_device=target_dev, target_pin=5,
                                              on_update=SetStatus('remote_pwm', 'ufloat1'))

        source_sens1 = ArduinoDigitalSensor(dev=0, pull_up_resistor=True, pin=2)
        source_sens2 = ArduinoAnalogSensor(dev=0, pin=0)

    class Remote(Group):
        awds1 = ArduinoRemoteDigitalSensor(dev=1, source_device=source_dev, pin=2) # receives via VW
        awds2 = ArduinoRemoteAnalogSensor(dev=1, source_device=source_dev, pin=0) # receives via VW


s = ArduinoSystem(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=1500,
            home_address=source_home,
            device_address=source_dev,
            virtualwire_tx_pin=11,
            virtualwire_rx_pin=10,
        ),
        ArduinoService(
            device="/dev/ttyUSB1",
            sample_rate=1500,
            home_address=target_home,
            device_address=target_dev,
            virtualwire_tx_pin=11,
            virtualwire_rx_pin=10,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
