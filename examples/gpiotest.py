from automate import *
from automate.program import Program


class mysys(System):
    s = RpioSensor(port=22, buttontype='down')
    a = RpioActuator(port=23, changedelay=2)
    p = Program(active_condition=Value(s),
                on_activate=SetStatus(a, True))

s = mysys(services=[
    # RpioService(),
    # TextUiService(),
],
    #exclude_services = ['RpioService']
    # exclude_services=['TextUiService']
)
# RpioService(), TextUiService()]
# main()
