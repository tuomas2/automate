from automate import *
from automate.program import Program


class mysys(System):
    #config = Config(print_level = logging.DEBUG)
    # Control servo with analog port a1 through interpolating sensor interp
    d12 = ArduinoDigitalSensor(dev=0, pin=12)

    d13 = ArduinoDigitalActuator(dev=0, pin=13)  # LED on Arduino board

    # pwm = ArduinoPWMActuator(dev = 0, pin = 4, slave = True)

    prog = Program(
        on_update=SetStatus(d13, d12)
    )

s = mysys(services=[ArduinoService(
    arduino_devs=["/dev/ttyUSB0"],
    arduino_dev_types=["Arduino"],
    arduino_dev_sampling=[500],
),
    TextUIService(),
    WebService(),
],
    #print_level= logging.DEBUG,
)
