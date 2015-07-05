#!/usr/bin/env python
"""
Factory example.

Two instances of system are running individually.
"""

from automate import *


def mysys(*args, **kwargs):
    class _mysys(System):
        mysensor = UserFloatSensor()
        myactuator = FloatActuator()

        # timers have cron syntax
        timer = CronTimerSensor("Timer 1",
                                timer_on="30 15 * * mon-thu;1 16 * * fri-sat,sun",
                                timer_off="30 8 * * mon-thu;0 10 * * fri-sat,sun")

        prog = Program(active_condition=Value(mysensor),
                       on_update=Run(
                           SetStatus(myactuator, 1),
                           Debug("Hello World!"),
                       )
                       )

    return _mysys(*args, **kwargs)


s1 = mysys(exclude_services=['TextUIService'], services=[WebService(http_port=8081)])
s2 = mysys(services=[WebService(http_port=8082)])