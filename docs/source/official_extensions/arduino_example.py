from automate import *


class MySystem(System):
    a1 = ArduinoAnalogSensor(dev=0, pin=0)
    d12 = ArduinoDigitalSensor(dev=0, pin=12)

    d13 = ArduinoDigitalActuator(dev=0, pin=13)  # LED on Arduino board
    servo = ArduinoServoActuator(min_pulse=200, max_pulse=8000, dev=0, pin=3, default=50, slave=True)

    interp = ConstantTimeActuator(change_time=2., change_frequency=20., slave_actuator=servo)

    prog = Program(
        on_update=Run(Log("Value: %s", Value(a1)), SetStatus(d13, d12), SetStatus(interp, Value(180) * Value(a1)))
    )

my_arduino = ArduinoService(
    arduino_devs=["/dev/ttyUSB0"],
    arduino_dev_types=["Arduino"],
    arduino_dev_sampling=[500])

s = MySystem(services=[my_arduino, WebService()])
