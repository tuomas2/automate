#!/usr/bin/env python
"""
Factory example
"""

from automate import *
from automate.program import Program


def mysys(*args, **kwargs):
    class _mysys(System):
        config = Config(logfile='helloworld.log')
        mysensor = UserFloatSensor(allow_web=True)
        myactuator = FloatActuator()  # "Actuator 1")

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

s1 = mysys(services=[GuiService(autostart=False),
                     TextUIService(),
                     WebService(autostart=True),
                     ])
s2 = mysys(services=[GuiService(autostart=False),
                     TextUIService(),
                     WebService(autostart=True, http_port=8081),
                     ])

s1.namespace['s2'] = s2
s1.text_ui()
