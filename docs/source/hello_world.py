from automate import *

class MySystem(System):
    # HW swtich connected Raspberry Pi GPIO port 1
    hardware_switch = RpioSensor(port=1)
    # Switch that is controllable, for example, from WEB interface
    web_switch = UserBoolSensor()
    # Lamp relay that switches lamp on/off, connected to GPIO port 2
    lamp = RpioActuator(port=2)
    # Program that controls the system behaviour
    program = Program(
        active_condition=Or('web_switch', 'hardware_switch'),
        on_activate=SetStatus('lamp', True)
    )


my_system = MySystem(
    services=[WebService()]
)
