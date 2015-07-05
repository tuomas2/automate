#!/usr/bin/env python
from automate import *


class mysys(System):
    mysensor = UserFloatSensor(
        on_update=Run(SetStatus('pwm', 'mysensor'), Shell('echo hep')),
    )
    pwm = RpioPWMActuator(port=18, dma_channel=0, frequency=50.)


s = mysys()
