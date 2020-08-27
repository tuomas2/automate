from automate import *
from automate.extensions.arduino import ArduinoPWMActuator

import platform
hostname = platform.node()


def clip_values(func):
    @wraps(func)
    def decorator(i, max_i, reverse=False):
        x = max(0., min(1., float(i)/max_i))
        if reverse:
            x = 1-x
        fx = func(x)
        return max(0., min(fx, 1.0))
    return decorator


@clip_values
def f1(x):
    return 4*x**2


@clip_values
def f2(x):
    if x < 0.5:
        return 0.
    return 4*x**2-4*x+1


@clip_values
def f3(x):
    return x**2


for f in [f1, f2, f3]:
    assert f(-1, 100) == 0.0
    assert f(0, 100) == 0.0
    assert f(100, 100) == 1.0
    assert f(101, 100) == 1.0


#def calc_val_warm(i, max_i, reverse=False):
#    return calc_val(2*i, max_i, reverse=reverse)

calc_val_warm = f1
calc_val_cold = f2


def calc_val_reverse(i, max_i):
    return f3(i, max_i, reverse=True)


class LampGroupsMixin:
    class LampsHardware(Group):
        cold_lamp_out = ArduinoPWMActuator(service=0, pin=3, default=0., history_length=1000)
        warm_lamp_out = ArduinoPWMActuator(service=0, pin=11, default=0., history_length=1000)  # 9,10 30 kHz

    class LampAdjustment(Group):
        tags ='adj'
        warm_preset1 = UserFloatSensor(value_min=0., value_max=1., default=1.)
        cold_preset1 = UserFloatSensor(value_min=0., value_max=1., default=1.)

        warm_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.3)
        cold_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.3)

        warm_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)
        cold_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)

        warm_preset4 = UserFloatSensor(value_min=0., value_max=1., default=.05)
        cold_preset4 = UserFloatSensor(value_min=0., value_max=1., default=.05)

        warm_preset5 = UserFloatSensor(value_min=0., value_max=1., default=.01)
        cold_preset5 = UserFloatSensor(value_min=0., value_max=1., default=.01)



    class Lamps(Group):
        tags = 'web'
        _toggler = IfElse('preset1', SetStatus('preset2', 1),
                          IfElse('preset2', SetStatus('preset3', 1),
                                 IfElse('preset3', SetStatus('preset3', 0),
                                        IfElse('preset4', SetStatus('preset4', 0),
                                               IfElse('preset5', SetStatus('preset5', 0),
                                                      SetStatus('preset1', 1))))))


        preset1 = UserBoolSensor(tags={'quick_lamps'},
                                 priority=2.,
                                 active_condition=Value('preset1'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset1'),
                                               SetStatus('cold_lamp_out', 'cold_preset1'),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               SetStatus('preset4', 0),
                                               SetStatus('preset5', 0),
                                               ))

        preset2 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset2'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset2'),
                                               SetStatus('cold_lamp_out', 'cold_preset2'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset3', 0),
                                               SetStatus('preset4', 0),
                                               SetStatus('preset5', 0),
                                               ))

        preset3 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset3'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset3'),
                                               SetStatus('cold_lamp_out', 'cold_preset3'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset4', 0),
                                               SetStatus('preset5', 0),
                                               ))

        preset4 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset4'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset4'),
                                               SetStatus('cold_lamp_out', 'cold_preset4'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               SetStatus('preset5', 0),
                                               ))

        preset5 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset5'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset5'),
                                               SetStatus('cold_lamp_out', 'cold_preset5'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               SetStatus('preset4', 0),
                                               ))

        switch_off = UserEventSensor(tags={'quick_lamps'}, on_activate=SetStatus(['fade_out', 'preset1', 'preset2', 'preset3', 'preset4', 'preset5'], [0]*6))

        _count = UserIntSensor(default=0)
        _max = UserIntSensor(default=100)
        fade_in_time = UserIntSensor(default=30*60)
        fade_out_time = UserIntSensor(default=10*60)

        _fade_in_warm_start = UserFloatSensor(default=0.0)
        _fade_in_cold_start = UserFloatSensor(default=0.0)

        _dimmer = Run(
            SetStatus(_count, 0),
            While(_count < _max,
                  SetStatus(_count, _count + 1),
                  SetStatus('warm_lamp_out', Func(calc_val_reverse, _count, _max) * _fade_in_warm_start),
                  SetStatus('cold_lamp_out', Func(calc_val_reverse, _count, _max) * _fade_in_cold_start),
                  Func(time.sleep, fade_out_time / _max),
                  do_after=SetStatus(['preset1', 'preset2', 'preset3', 'preset4', 'preset5', 'fade_out', '_count'], [0]*5)
                  )
        )

        _lighter = Run(
            SetStatus(_count, 0),
            While(_count < _max,
                  SetStatus(_count, _count + 1),
                  SetStatus('warm_lamp_out', Func(calc_val_warm, _count, _max) * Value('warm_preset1')),
                  SetStatus('cold_lamp_out', Func(calc_val_cold, _count, _max) * Value('cold_preset1')),
                  Func(time.sleep, fade_in_time / _max),
                  do_after=SetStatus(['preset1', 'fade_in', '_count'], [1, 0, 0]))
        )

        fade_in = UserBoolSensor(active_condition=Value('fade_in'), tags='quick_lamps',
                                 on_activate=Run(
                                     '_lighter'))

        fade_out = UserBoolSensor(tags={'quick_lamps'}, priority=3,
                                     active_condition=Value('fade_out'),
                                     on_activate=Run(
                                         SetStatus([_fade_in_cold_start, _fade_in_warm_start], ['cold_lamp_out', 'warm_lamp_out']),
                                         '_dimmer')
                                  )

    class Aquarium(Group):
        tags = 'adj'
        warm_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=1)
        cold_preset_akva = UserFloatSensor(value_min=0., value_max=1., default=0.5)

        akvadimmer = UserBoolSensor(
            priority=1.0, # lower priority light for aquarium (raspi1) remote use only
            active_condition=Value('akvadimmer'),
            on_activate=
            IfElse(
                # if lamp already on, do not activate this function at all
                Or('warm_lamp_out', 'cold_lamp_out'),
                SetStatus('akvadimmer', 0),
                Run(
                    SetStatus(['_fade_in_cold_start', '_fade_in_warm_start'], [cold_preset_akva, warm_preset_akva]),
                    Run('_dimmer'),
                    )
            )
        )

    class AlarmClock(Group):
        tags = 'adj'
        alarm_clock = CronTimerSensor(timer_on='45 6 * * *', timer_off='0 9 * * *',
                                      active_condition=And('alarm_enabled', Value('alarm_clock')),
                                      on_activate=SetStatus('fade_in', True))

        alarm_enabled = UserBoolSensor(tags={'quick_lamps', 'web'}, default=hostname == 'raspi3')
