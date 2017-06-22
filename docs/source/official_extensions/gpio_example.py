from automate import *


class MySystem(System):
    button = RpioSensor(port=22, button_type='down')
    light = RpioActuator(port=23, change_delay=2)
    myprog = Program(active_condition=Value('mysensor'),
                     on_activate=SetStatus('myactuator', True))

mysystem = MySystem(services=[WebService()])
