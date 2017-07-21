from logging.config import dictConfig
import pyfirmata

from automate.extensions.arduino import arduino_service

from automate.extensions.arduino.arduino_sensors import ArduinoVirtualWireAbstractSensor



from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService, ArduinoVirtualWireActuator, ArduinoVirtualWireMessageSensor
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
        on_activate=VirtualWireCommand(0, 1, pyfirmata.SET_PIN_MODE, 13, pyfirmata.OUTPUT)
    )

    ubool2 = UserBoolSensor(
        on_update=VirtualWireCommand(0, 1, pyfirmata.DIGITAL_MESSAGE, 13, 'ubool2')
    )

    ufloat1 = UserFloatSensor(value_min=0, value_max=1)

    d13_0 = ArduinoDigitalActuator(dev=0, pin=13,
                                   on_update=SetStatus('d13_0', 'ubool'))
    d13_1 = ArduinoDigitalActuator(dev=1, pin=13,
                                   on_update=SetStatus('d13_1', 'ubool'))

    vwsensor0 = ArduinoVirtualWireMessageSensor(dev=0, pin=10)
    vwactuator0 = ArduinoVirtualWireActuator(dev=0, pin=11,
        on_update=SetStatus('vwactuator0', ustr0)
    )

    vwsensor1 = ArduinoVirtualWireMessageSensor(dev=1, pin=10)
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
    event2 = UserEventSensor(
        on_activate=VirtualWireCommand(0, 1, arduino_service.SET_VIRTUAL_PIN_VALUE, 1, arduino_service.TYPE_INT, 5)
    )

    event3 = UserEventSensor(
        on_activate=VirtualWireCommand(0, 1, arduino_service.SET_VIRTUAL_PIN_VALUE, 1, arduino_service.TYPE_STR, "test")
    )

    event4 = UserEventSensor(
        on_activate=VirtualWireCommand(0, 1, arduino_service.SET_VIRTUAL_PIN_VALUE, 1, arduino_service.TYPE_FLOAT, arduino_service.float_to_bytes(0.5))
    )

    ubool2 = UserBoolSensor(
        on_update=VirtualWireCommand(0, 1, arduino_service.SET_DIGITAL_PIN_VALUE, 13, 'ubool2')
    )

    #ufloat1 = UserFloatSensor(value_min=0, value_max=1)

#    d13_0 = ArduinoDigitalActuator(dev=0, pin=13,
#                                   on_update=SetStatus('d13_0', 'ubool'))
#    d13_1 = ArduinoDigitalActuator(dev=1, pin=13,
#                                   on_update=SetStatus('d13_1', 'ubool'))

#    vwsensor0 = ArduinoVirtualWireMessageSensor(dev=0, pin=10)
    vwactuator0 = ArduinoVirtualWireActuator(dev=0,
        recipient=1,
        # TODO these settings shoudl be per device
        on_update=SetStatus('vwactuator0', ustr0),
    )

    vwsensor1a = ArduinoVirtualWireMessageSensor(dev=1)
    vwsensor1b = ArduinoVirtualWireMessageSensor(dev=1)

    vwsensor_vpin1 = ArduinoVirtualWireAbstractSensor(dev=1, virtual_pin=1)
    vwsensor_vpin2 = ArduinoVirtualWireAbstractSensor(dev=1, virtual_pin=2)
#    vwactuator1 = ArduinoVirtualWireActuator(dev=1, pin=11,
#        on_update=SetStatus('vwactuator1', ustr1)
#    )


s = mysys2(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=500,
            home_address=1,
            device_address=1,
            virtualwire_tx_pin=11,
            virtualwire_rx_pin=10,
        ),
        ArduinoService(
            device="/dev/ttyUSB1",
            sample_rate=500,
            home_address=1,
            device_address=2,
            virtualwire_tx_pin=11,
            virtualwire_rx_pin=10,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
