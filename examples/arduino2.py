from automate import *
from automate.extensions.arduino import ArduinoDigitalSensor, ArduinoDigitalActuator, \
    ArduinoService, ArduinoVirtualWireActuator
from automate.extensions.webui import WebService
from automate.program import Program


class mysys(System):
    #config = Config(print_level = logging.DEBUG)
    # Control servo with analog port a1 through interpolating sensor interp
    ustr = UserStrSensor()
    ubool = UserBoolSensor()
    d12 = ArduinoDigitalSensor(dev=0, pin=12)

    d13 = ArduinoDigitalActuator(dev=0, pin=13)  # LED on Arduino board

    vw = ArduinoVirtualWireActuator(dev=0, pin=10)

    prog = Program(
        on_update=Run(SetStatus(d13, ubool), SetStatus(vw, ustr))
    )

s = mysys(
    services=[ArduinoService(
        arduino_devs=["/dev/ttyUSB0"],
        arduino_dev_types=["Arduino"],
        arduino_dev_sampling=[500],
    ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
