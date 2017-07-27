from automate import *


class MySystem(System):
    ufloat = UserFloatSensor(value_min=0, value_max=1)

    a1 = ArduinoAnalogSensor(service=0, pin=0)
    d12 = ArduinoDigitalSensor(service=0, pin=12)

    d13 = ArduinoDigitalActuator(service=0, pin=13)  # LED on Arduino board
    pwm = ArduinoPWMActuator(service=0, pin=4, on_update=SetStatus('pwm', 'ufloat'))
    servo = ArduinoServoActuator(min_pulse=200,
                                 max_pulse=8000,
                                 service=0,
                                 pin=3,
                                 default=50,
                                 slave=True)

    interp = ConstantTimeActuator(change_time=2.,
                                  change_frequency=20.,
                                  slave_actuator=servo)

    prog = Program(
        on_update=Run(Log("Value: %s", Value(a1)),
                      SetStatus(d13, d12),
                      SetStatus(interp, Value(180) * Value(a1)))
    )

my_arduino = ArduinoService(
    device="/dev/ttyUSB0",
    sample_rate=500,
)

s = MySystem(services=[my_arduino, WebService()])
