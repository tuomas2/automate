from automate import *

"""

    Listens port 9192 and sets status of ``out`` according to the
    input given from socket.
"""


class mysys(System):
    sock = SocketSensor(port=9192)
    out = RpioActuator(port=17, safety_delay=30, safety_mode='both', default=False)

    prg = Program(active_condition=Value(sock),
                  on_activate=SetStatus(out, sock),
                  )

s = mysys()
