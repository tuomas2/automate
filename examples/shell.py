from automate import *
from automate.program import Program

t = IntervalTimerSensor(interval=10)
p = Program(
    triggers=[t],
    on_update=Log(Shell('ls'))
)
main()
