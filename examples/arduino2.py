from automate import *
from automate.extensions.arduino import ArduinoDigitalSensor, ArduinoDigitalActuator, \
    ArduinoService, ArduinoVirtualWireActuator, ArduinoVirtualWireSensor
from automate.extensions.webui import WebService
from automate.program import Program


class mysys(System):
    #config = Config(print_level = logging.DEBUG)
    # Control servo with analog port a1 through interpolating sensor interp
    ustr = UserStrSensor()
    ubool = UserBoolSensor()

    d13 = ArduinoDigitalActuator(dev=0, pin=13)  # LED on Arduino board

    vwactuator = ArduinoVirtualWireActuator(dev=1, pin=10)
    #d11 = ArduinoDigitalSensor(dev=0, pin=11)
    vwsensor = ArduinoVirtualWireSensor(dev=0, pin=10)

    prog = Program(
        on_update=Run(SetStatus(d13, ubool), SetStatus(vwactuator, ustr))
    )

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
