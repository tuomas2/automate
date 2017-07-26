from automate import *
from automate.program import Program


class ArduinoSystem(System):
    # Control servo with analog port a1 through interpolating sensor interp
    a1 = ArduinoAnalogSensor(dev=0, pin=0)
    d12 = ArduinoDigitalSensor(dev=0, pin=12)

    d13 = ArduinoDigitalActuator(dev=0, pin=13)  # LED on Arduino board
    servo = ArduinoServoActuator(min_pulse=200, max_pulse=8000, dev=0, pin=3, default=50, slave=True)

    # pwm = ArduinoPWMActuator(dev = 0, pin = 4, slave = True)
    interp = ConstantTimeActuator(ctime=2., changefreq=20., slaveactuator=servo)

    prog = Program(
        triggers=[a1],
        on_update=Run(Log("Value: %s", Value(a1)), SetStatus(d13, d12), SetStatus(interp, Value(180) * Value(a1)))
    )

s = ArduinoSystem(services=[ArduinoService(
    device="/dev/ttyUSB0",
    device_type="arduino",
    sample_rate=500,
),
    TextUIService(),
],
)
