#!/usr/bin/env python

"""
Example with two systems running simultaneously

"""

from automate import *
from automate.program import Program


class mysys1(System):
    mysensor = UserFloatSensor()
    myactuator = FloatActuator()

    # timers have cron syntax
    timer = CronTimerSensor(timer_on="30 15 * * mon-thu;1 16 * * fri-sat,sun",
                            timer_off="30 8 * * mon-thu;0 10 * * fri-sat,sun")

    prog = Program(active_condition=Value(mysensor),
                   on_update=Run(
                       SetStatus(myactuator, 1),
                       Debug("Hello World!"),
                   )
                   )


class mysys2(System):
    mysensor2 = UserFloatSensor()
    myactuator2 = FloatActuator()

    # timers have cron syntax
    timer = CronTimerSensor(timer_on="30 15 * * mon-thu;1 16 * * fri-sat,sun",
                            timer_off="30 8 * * mon-thu;0 10 * * fri-sat,sun")

    prog2 = Program(active_condition=Value(mysensor2),
                    on_update=Run(
                        SetStatus(myactuator2, 1),
                        Debug("Hello World!"),
                    )
                    )


s1 = mysys1(exclude_services=['TextUIService'],
            services=[WebService()])

s2 = mysys2(services=[WebService(http_port=8081)])
