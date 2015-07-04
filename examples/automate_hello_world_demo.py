#!/usr/bin/env python

from automate import *
from automate.program import Program


class mysys(System):

    class mygroup(Group):

        class mygrp2(Group):
            mysensor = UserBoolSensor(tags='web')
        act2 = FloatActuator(priorities={'myactuator': -1})
    myactuator = FloatActuator(
        #on_update = Run(Log('hep hep'), SetStatus(act2, 'myactuator'), Log('jep %s', ToStr('myactuator')))
        on_update=Run(Log('hep hep'), SetStatus(mygroup.act2), Log('jep %s', ToStr('myactuator')))
    )  # "Actuator 1")

    # timers have cron syntax
    timer = CronTimerSensor(
        timer_on="30 15 * * mon-thu;1 16 * * fri-sat,sun",
        timer_off="30 8 * * mon-thu;0 10 * * fri-sat,sun"
    )

    prog = Program(active_condition=Value(mygroup.mygrp2.mysensor),
                   on_update=Run(
                       SetStatus(myactuator, 1),
                       Debug("Hello World!"),
    )
    )


s = mysys(services=[  # GuiService(),
    # TextUiService(),
    # RpcService(
    #),
    WebService(
        # ssl_certificate="testi.crt",
        # ssl_private_key="testi.key",
        # http_port=4430,
        #http_auth=('tuomas', 'mp2gra5'),


    ),
    #DjangoWebService(slave=True, http_port=8081),
    # StatusSaverService(),
],
    #statusdata = {'mysensor': 1},
    #print_level = logging.DEBUG,
    print_level=logging.INFO,
)
# s.text_ui()
