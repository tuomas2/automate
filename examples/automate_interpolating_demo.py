#!/usr/bin/env python
# encoding: utf-8

from automate import *
from automate.program import Program


class mysys(System):
    sensori = UserFloatSensor()
    targetti = ConstantTimeActuator(ctime=5.0, changefreq=10.,
                                    slaveactuator=PWMActuator(port=-1, slave=True, default=0.0))
    targetti2 = ConstantSpeedActuator(speed=1.0, changefreq=10.,
                                      slaveactuator=PWMActuator(port=-1, slave=True, default=0.0))

    prog = Program(
        on_update=Run(Log("Test!"), SetStatus(targetti, sensori), SetStatus(targetti2, sensori))
    )

s = mysys(services=WebService())
