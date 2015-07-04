from automate import *
from automate.program import Program

"""
This example has 2 sensors, for example buttons in bumpers of a car.
When car collides, it changes direction (motor input voltages are driven by 
actuators m1 and m2).

There is also a failsafe that stops the car if there is no collisions in 15
seconds.
"""

s1 = RpioSensor(port=14, allow_web=True)
s2 = RpioSensor(port=15, allow_web=True)
m1 = RpioActuator(port=23)
m2 = RpioActuator(port=24)

p = Program("normal",
            on_activate=Run(SetStatus(m1, 1), SetStatus(m2, 1)),
            on_update=Run(If(Changed(s1), Run(SetStatus(m1, 1), SetStatus(m2, 0))),
                          If(Changed(s2), Run(SetStatus(m1, 0), SetStatus(m2, 1))))
            )

t = IntervalTimerSensor(interval=5)

failsafe = Program("failsafe",
                   triggers=[t],
                   active_condition=(Eval("time.time()", "import time") -
                                     Max(Attrib(s1, "_last_changed"), Attrib(s2, "_last_changed")) > Value(15)),
                   on_activate=Run(SetStatus(m1, 0), SetStatus(m2, 0)),
                   priority=2
                   )
main()
