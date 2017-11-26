from automate import *
from automate.extensions.arduino import ArduinoAnalogSensor, ArduinoDigitalSensor, \
    ArduinoServoActuator, ArduinoDigitalActuator, ArduinoService
from automate.extensions.arduino.arduino_actuators import ArduinoLCDActuator
from automate.extensions.webui import WebService
from automate.program import Program

def multiply(value):
    return 2*value

class ArduinoSystem(System):
    # Control servo with analog port a1 through interpolating sensor interp
    u1 = UserFloatSensor(status_filter=multiply, value_min=0, value_max=1)
    u2 = UserFloatSensor(history_frequency=1, value_min=0, value_max=1)
    a1 = ArduinoAnalogSensor(service=0, pin=0)
    d12 = ArduinoDigitalSensor(service=0, pin=12, pull_up_resistor=True, inverted=True)

    d13 = ArduinoDigitalActuator(service=0, pin=13)  # LED on Arduino board
    #servo = ArduinoServoActuator(min_pulse=200, max_pulse=8000, service=0, pin=3, default=50, slave=True)

    # pwm = ArduinoPWMActuator(dev = 0, pin = 4, slave = True)
    #interp = ConstantTimeActuator(change_time=2., change_frequency=20., slave_actuator=servo)

    u3 = UserStrSensor(on_update=SetStatus('lcd', 'u3'))

    lcd = ArduinoLCDActuator()

    #prog = Program(
   # #    triggers=[a1],
   #     on_update=Run(Log("Value: %s", Value(a1)), SetStatus(d13, d12), SetStatus(interp, Value(180) * Value(a1)))
   # )

s = ArduinoSystem(
    services=[ArduinoService(
        device="/dev/ttyUSB0",
        device_type="arduino",
        instant_digital_reporting=False,
        sample_rate=2500,
        log_level=logging.DEBUG,
),
    WebService(read_only=False),
    TextUIService(),
],
)
