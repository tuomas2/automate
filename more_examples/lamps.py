from automate import *
from automate.extensions.arduino import ArduinoPWMActuator


def calc_val(i, max_i, reverse=False):
    """
    Must return value between 0 and 1.
    """
    x = max(0., min(1., float(i)/max_i))
    if reverse:
        x = 1-x

    return max(0., min(x**2, 1.0))


def calc_val_reverse(i, max_i):
    return calc_val(i, max_i, reverse=True)


def get_lamps_group(enable_alarm=False):
    class Lamps(Group):
        _toggler = IfElse('preset1', SetStatus('preset2', 1),
                          IfElse('preset2', SetStatus('preset3', 1),
                                 IfElse('preset3', SetStatus('preset3', 0),
                                        SetStatus('preset1', 1))))

        cold_lamp_out = ArduinoPWMActuator(dev=0, pin=9, default=0.)
        warm_lamp_out = ArduinoPWMActuator(dev=0, pin=10, default=0.)  # 9,10 30 kHz

        warm_preset1 = UserFloatSensor(value_min=0., value_max=1., default=1.)
        cold_preset1 = UserFloatSensor(value_min=0., value_max=1., default=1.)

        warm_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.4)
        cold_preset2 = UserFloatSensor(value_min=0., value_max=1., default=.4)

        warm_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)
        cold_preset3 = UserFloatSensor(value_min=0., value_max=1., default=.1)

        preset1 = UserBoolSensor(tags={'quick_lamps'},
                                 priority=2.,
                                 active_condition=Value('preset1'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset1'),
                                               SetStatus('cold_lamp_out', 'cold_preset1'),
                                               SetStatus('preset2', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset2 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset2'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset2'),
                                               SetStatus('cold_lamp_out', 'cold_preset2'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset3', 0),
                                               ))

        preset3 = UserBoolSensor(tags={'quick_lamps'}, priority=2.,
                                 active_condition=Value('preset3'),
                                 on_update=Run(SetStatus('warm_lamp_out', 'warm_preset3'),
                                               SetStatus('cold_lamp_out', 'cold_preset3'),
                                               SetStatus('preset1', 0),
                                               SetStatus('preset2', 0),
                                                ))

        switch_off = UserEventSensor(tags={'quick_lamps'}, on_activate=SetStatus(['fade_out', 'preset1', 'preset2', 'preset3'], [0]*4))

        _count = UserIntSensor(default=0)
        _max = UserIntSensor(default=100)
        fade_in_time = UserIntSensor(default=1800)
        fade_out_time = UserIntSensor(default=1800)

        _fade_in_warm_start = UserFloatSensor(default=0.0)
        _fade_in_cold_start = UserFloatSensor(default=0.0)

        _dimmer = Run(
            SetStatus(_count, 0),
            While(_count < _max,
                  SetStatus(_count, _count + 1),
                  SetStatus(warm_lamp_out, Func(calc_val_reverse, _count, _max) * _fade_in_warm_start),
                  SetStatus(cold_lamp_out, Func(calc_val_reverse, _count, _max) * _fade_in_cold_start),
                  Func(time.sleep, fade_out_time / _max),
                  do_after=SetStatus(['preset1', 'preset2', 'preset3', 'fade_out', '_count'], [0]*5)
                  )
        )

        _lighter = While(_count < _max,
                         SetStatus(_count, _count + 1),
                         SetStatus(warm_lamp_out, Func(calc_val, _count, _max) * warm_preset1),
                         SetStatus(cold_lamp_out, Func(calc_val, _count, _max) * cold_preset1),
                         Func(time.sleep, fade_in_time / _max),
                         do_after=SetStatus(['preset1', 'fade_in', '_count'], [1, 0, 0]))

        fade_in = UserBoolSensor(active_condition=Value('fade_in'),
                                 on_activate=Run(
                                     '_lighter'))

        fade_out = UserBoolSensor(tags={'quick_lamps'}, priority=3,
                                     active_condition=Value('fade_out'),
                                     on_activate=Run(
                                         SetStatus([_fade_in_cold_start, _fade_in_warm_start], [cold_lamp_out, warm_lamp_out]),
                                         '_dimmer')
                                 )
        alarm_clock = CronTimerSensor(timer_on='0 7 * * *', timer_off='0 9 * * *',
                                      active_condition=And('alarm_enabled', Value('alarm_clock')),
                                      on_activate=SetStatus(fade_in, True))

        alarm_enabled = UserBoolSensor(default=enable_alarm)

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
                    SetStatus([_fade_in_cold_start, _fade_in_warm_start], [cold_preset_akva, warm_preset_akva]),
                    Run('_dimmer'),
                    )
            )
        )

    return Lamps
