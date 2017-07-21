from logging.config import dictConfig

from pyfirmata import SET_PIN_MODE, OUTPUT, DIGITAL_MESSAGE

SET_DIGITAL_PIN_VALUE = 0xF5

from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService, ArduinoVirtualWireActuator, ArduinoVirtualWireSensor
from automate.extensions.arduino.arduino_callables import VirtualWireCommand, VirtualWireMessage
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


class mysys(System):
    ustr0 = UserStrSensor()
    ustr1 = UserStrSensor()
    ubool = UserBoolSensor()

    ubool1 = UserEventSensor(
        on_activate=VirtualWireCommand(0, 1, SET_PIN_MODE, 13, OUTPUT)
    )

    ubool2 = UserBoolSensor(
        on_update=VirtualWireCommand(0, 1, DIGITAL_MESSAGE, 13, 'ubool2')
    )

    ufloat1 = UserFloatSensor(value_min=0, value_max=1)

    d13_0 = ArduinoDigitalActuator(dev=0, pin=13,
                                   on_update=SetStatus('d13_0', 'ubool'))
    d13_1 = ArduinoDigitalActuator(dev=1, pin=13,
                                   on_update=SetStatus('d13_1', 'ubool'))

    vwsensor0 = ArduinoVirtualWireSensor(dev=0, pin=10)
    vwactuator0 = ArduinoVirtualWireActuator(dev=0, pin=11,
        on_update=SetStatus('vwactuator0', ustr0)
    )

    vwsensor1 = ArduinoVirtualWireSensor(dev=1, pin=10)
    vwactuator1 = ArduinoVirtualWireActuator(dev=1, pin=11,
        on_update=SetStatus('vwactuator1', ustr1)
    )

    # Using PWM on pins 9/10 will break VirtualWire.
    # pwmactuator1 = ArduinoPWMActuator(dev=0, pin=9,
    #   on_update=SetStatus('pwmactuator1', ufloat1)
    #)



class mysys2(System):
    ustr0 = UserStrSensor()
    ustr1 = UserStrSensor()
    ubool = UserBoolSensor()

    event1 = UserEventSensor(
        on_activate=VirtualWireMessage(0, 1, 'test test')
    )

    ubool2 = UserBoolSensor(
        on_update=VirtualWireCommand(0, 1, SET_DIGITAL_PIN_VALUE, 13, 'ubool2')
    )

    #ufloat1 = UserFloatSensor(value_min=0, value_max=1)

#    d13_0 = ArduinoDigitalActuator(dev=0, pin=13,
#                                   on_update=SetStatus('d13_0', 'ubool'))
#    d13_1 = ArduinoDigitalActuator(dev=1, pin=13,
#                                   on_update=SetStatus('d13_1', 'ubool'))

#    vwsensor0 = ArduinoVirtualWireSensor(dev=0, pin=10)
    vwactuator0 = ArduinoVirtualWireActuator(dev=0, pin=11,
        recipient=1,
        # TODO these settings shoudl be per device
        on_update=SetStatus('vwactuator0', ustr0),
    )

    vwsensor1 = ArduinoVirtualWireSensor(dev=1, pin=10)
#    vwactuator1 = ArduinoVirtualWireActuator(dev=1, pin=11,
#        on_update=SetStatus('vwactuator1', ustr1)
#    )


s = mysys2(
    services=[ArduinoService(
        arduino_devs=["/dev/ttyUSB0", "/dev/ttyUSB1"], # TODO should be 1 device per Service, and multiple Services
        arduino_dev_types=["Arduino", 'Arduino'],
        arduino_dev_sampling=[500, 500],
        home_address=1,
        device_address=1, # TODO this should be a list (per actual arduino device)...
    ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
