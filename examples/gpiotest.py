from automate import *


class mysys(System):
    s = RpioSensor(port=22, buttontype='down')
    a = RpioActuator(port=23, changedelay=2)
    p = Program(active_condition=Value(s),
                on_activate=SetStatus(a, True))

s = mysys()