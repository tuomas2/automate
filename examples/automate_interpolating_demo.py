#!/usr/bin/env python
# encoding: utf-8

from automate import *
from automate.program import Program


class mysys(System):
    sensori = UserFloatSensor()
    slave1 = FloatActuator(slave=True, default=0.0)
    targetti = ConstantTimeActuator(change_time=5.0, change_frequency=10.,
                                    slave_actuator=slave1)
    slave2 = FloatActuator(slave=True, default=0.0)
    targetti2 = ConstantSpeedActuator(speed=1.0, change_frequency=10.,
                                      slave_actuator=slave2)

    prog = Program(
        on_update=Run(Log("Test!"), SetStatus(targetti, sensori), SetStatus(targetti2, sensori))
    )

s = mysys(services=[WebService(read_only=False)])
