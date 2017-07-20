from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService, ArduinoVirtualWireActuator, ArduinoVirtualWireSensor
from automate.extensions.webui import WebService


class mysys(System):
    ustr0 = UserStrSensor()
    ustr1 = UserStrSensor()
    ubool = UserBoolSensor()
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

s = mysys(
    services=[ArduinoService(
        arduino_devs=["/dev/ttyUSB0", "/dev/ttyUSB1"],
        arduino_dev_types=["Arduino", 'Arduino'],
        arduino_dev_sampling=[500, 500],
    ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
