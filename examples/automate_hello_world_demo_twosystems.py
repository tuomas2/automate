#!/usr/bin/env python


from automate import *
from automate.program import Program


class mysys1(System):
    config = Config(print_level=logging.DEBUG, logfile='helloworld.log')
    mysensor = UserFloatSensor(allow_web=True)
    myactuator = FloatActuator()  # "Actuator 1")

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
    config = Config()  # logfile='helloworld.log')
    mysensor2 = UserFloatSensor(allow_web=True)
    myactuator2 = FloatActuator()  # "Actuator 1")

    # timers have cron syntax
    timer = CronTimerSensor(timer_on="30 15 * * mon-thu;1 16 * * fri-sat,sun",
                            timer_off="30 8 * * mon-thu;0 10 * * fri-sat,sun")

    prog2 = Program(active_condition=Value(mysensor2),
                    on_update=Run(
        SetStatus(myactuator2, 1),
        Debug("Hello World!"),
    )
    )

s1 = mysys1(services=[GuiService(autostart=False),
                      # TextUiService(),
                      WebService(autostart=True, allow_exec=True),
                      ])

s2 = mysys2(services=[GuiService(autostart=False),
                      # TextUiService(),
                      WebService(autostart=True, http_port=8081, allow_exec=True),
                      ])

#                      WebService(autostart=True, http_port=8081),
#s = mysys(services = [TextUiService()])
# s1.text_ui()
