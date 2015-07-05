from automate import *

class demo(System):
    t = IntervalTimerSensor(interval=3)
    p = Program(
        triggers=[t],
        on_update=Log(Shell('/bin/ls', output=True))
    )

d = demo()
