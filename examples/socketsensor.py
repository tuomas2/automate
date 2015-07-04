from automate import *
from automate.program import Program


class mysys(System):
    sock = SocketSensor(port=9192)
    out = RpioActuator(port=17, safetydelay=30, safetymode='both', default=False)

    prg = Program(active_condition=Value(sock),
                  on_activate=SetStatus(out, sock),
                  )

s = mysys(services=[TextUIService(), RpioService()])
s.text_ui()
