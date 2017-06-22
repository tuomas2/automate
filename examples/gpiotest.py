from automate import *


class mysys(System):
    s = RpioSensor(port=22, button_type='down')
    a = RpioActuator(port=23, change_delay=2)
    p = Program(active_condition=Value(s),
                on_activate=SetStatus(a, True))

s = mysys()