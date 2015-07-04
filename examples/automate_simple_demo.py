#!/usr/bin/env python
# encoding: utf-8

from automate import *
from automate.program import Program

config = get_config()

config.set(
    debug=False,
    autosave_interval=10 * 60,
    http_auth=(
        ('automate_admin', 'password'),
    )
)


def initialize():
    mysensor = UserFloatSensor("Sensor 1")
    myactuator = FloatActuator("Actuator 1")

    # timers have cron syntax
    timer = CronTimerSensor("Timer 1",
                            timer_on="0,10,20,30,40,50 * * * *",
                            timer_off="5,15,25,35,45,55 * * * *")

    prog = Program("Program 1",
                   active_condition=Value(timer),
                   # on_activate=
                   on_update=SetStatus(myactuator, mysensor),
                   )


if __name__ == '__main__':
    if not load_state():
        initialize()
    main()
