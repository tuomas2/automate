#!/usr/bin/env python
# encoding: utf-8

""" A more advanced example program implementing some aquarium automatization
  Read through and try to understand. Some helpful comments inside.

  A more through tutorial is on my TODO list.


"""

from automate import *
from automate.program import Program
from automate.statusobject import AbstractActuator


class munsysteemi(System):
    #system = SystemReference()
    autosave_interval = 10 * 60,  # autosave every 10 minutes
    logfile = "autoaqualog.txt",
    http_auth = (
        ('mylogin', 'mypassword'),
    ),
    # GPIO pin configuration
    relays = [14, 15, 18, 23, 24, 25, 8, 7]
    relays.reverse()
    bread = [17, 27, 22, 10, 9, 11, 2, 3]  # port 4 is reserved for temperature sensor

    # First define some sensors

    # These are GPIO sensors that detect water leakage in various places
    valutusputki = RpioSensor(port=bread[0])
    vetta_yli_altaan = RpioSensor(port=bread[1])
    palkit = RpioSensor(port=bread[2])
    ala_altaat_ylaraja = RpioSensor(port=bread[3])

    aqua_temperature = TemperatureSensor(addr="28-00000558263c",
                                         interval=60,
                                         status=25)
    alarm = PWMActuator(port=bread[4], default=0, frequency=100, safetydelay=0)
    # else:
    #    aqua_temperature = FloatSensor(status=25)
    #    alarm = ProgramActuator(prog="notify.sh", default=0, execmode="rising", safety_delay=0)

    cpu_temperature = CPUTemperatureSensor(interval=5,
                                           status=25)

    ph = UserFloatSensor(status=6.5)
    waterfailure_manual_switch = UserBoolSensor(status=0, allow_web=True, tags="switch")
    light_manual_mode = UserBoolSensor(status=1, allow_web=True, tags="switch")
    holiday_mode = UserBoolSensor(status=0, allow_web=True, tags="switch")
    test_mode_switch = UserBoolSensor(status=0, allow_web=True, tags="switch")
    lamp_manual_switch = UserBoolSensor(status=0, allow_web=True)

    not_enough_water_in_the_sump = UserBoolSensor(status=0)
    electricity_on = UserBoolSensor(status=1)
    sump_full = UserBoolSensor(status=0)

    # Then define some actuators
    uvc_filter = RelayActuator(port=relays[0], default=0)
    mainpump = RelayActuator(port=relays[1], default=1, safetydelay=60 * 2, safetymode="rising")
    co2pump = RelayActuator(port=relays[2], default=1, safetydelay=60 * 2, safetymode="rising")
    co2inj = RelayActuator(port=relays[3], default=0, safetydelay=60 * 2, safetymode="rising")
    heater = RelayActuator(port=relays[4], default=1, safetydelay=5, safetymode="both")

    # My lamp setup is the following: I have three lamps and I want to switch them on with 7 minute intervals.
    # They are HQI lamps so I have 30 minutes safety_delay to not break them with too quick switch-on/switch-offs

    lampsafety = 30 * 60
    lamp1 = RelayActuator(port=relays[5], safetydelay=lampsafety, safetymode="rising")
    lamp2 = RelayActuator(port=relays[6], safetydelay=lampsafety, safetymode="rising")
    lamp3 = RelayActuator(port=relays[7], safetydelay=lampsafety, safetymode="rising")
    lamps = BoolActuator(safetydelay=lampsafety, safetymode="rising")

    lampdelay = 7 * 60
    lampswitchprog = Program(
        "Lamp switch prog",
        triggers=[lamps],
        on_activate=Run(SetStatus(lamp1, lamps), SetStatus(lamp2, lamps), SetStatus(lamp3, lamps)),
        on_update=Run(SetStatus(lamp1, lamps),
                      Delay(lampdelay, SetStatus(lamp2, lamps)),
                      Delay(2 * lampdelay, SetStatus(lamp3, lamps))),
    )

    emailer = EmailActuator(to_email="",
                            smtp_hostname="smtp.googlemail.com",
                            smtp_username="",
                            smtp_password="",
                            smtp_fromemail="",
                            smtp_fromname="",
                            )

    # Timers
    co2_timer = CronTimerSensor(u"CO2 timer",
                                timer_on="30 5 * * *",
                                timer_off="30 15 * * *")

    co2_timer_holiday = CronTimerSensor("CO2 holiday-timer",
                                        timer_on="30 5 * * *",
                                        timer_off="30 12 * * *",
                                        tags="holiday")

    lamps_timer = CronTimerSensor(timer_on="0 10 * * *",
                                  timer_off="0 20 * * mon-thu; 0 22 * * fri-sat,sun")

    lamps_timer_holiday = CronTimerSensor("Lamp holiday-timer",
                                          timer_on="0 10 * * *",
                                          timer_off="0 15 * * *",
                                          tags="holiday")

    # Then define programs

    # Triggers and targets for a program are collected automatically from on_update,
    # on_activate, on_deactivate, active_condition and update_condition callables
    # So, for example here on_update is activated if holiday_mode or timer sensors
    # are changed.

    timerprog = Program(on_update=IfElse(holiday_mode,
                                         Run(SetStatus(lamps, lamps_timer_holiday),
                                             SetStatus(co2inj, co2_timer_holiday),
                                             SetStatus(uvc_filter, lamps_timer_holiday)),
                                         Run(SetStatus(lamps, lamps_timer),
                                             SetStatus(co2inj, co2_timer),
                                             SetStatus(uvc_filter, lamps_timer))),
                        priority=1.5
                        )

    lamps_manual_prog = Program(active_condition=Value(light_manual_mode),
                                on_update=SetStatus(lamps, lamp_manual_switch),
                                priority=3,
                                )

    # Send email if CPU is burning
    cpuprog = Program(active_condition=cpu_temperature > Value(60),
                      on_activate=Run(SetStatus(alarm, 50), Swap(emailer)),
                      priority=2
                      )

    # Automatically switch heater on or off according to temperature
    heaterprog = Program(on_update=SetStatus(heater, aqua_temperature < Value(25)),
                         priority=1,
                         )

    # beeb-beeb
    alarminterval = IntervalTimerSensor(interval=0.25)

    # Actuators can be used as a trigger as well. Here I am using this BinaryActuator as such.
    # Actuator status can be set by many different programs. The active programs are sorted by
    # their priority in actuator and the actual status of actuator is determined by the program
    # with highest priority.

    alarmtrigger = BoolActuator(safetydelay=0)

    alarmprog = Program(active_condition=Value(alarmtrigger),
                        on_update=SetStatus(alarm, Product(Value(50.), alarminterval))
                        )

    waterfailure_lattia = Program(active_condition=And(Or(valutusputki,
                                                          vetta_yli_altaan,
                                                          palkit,
                                                          waterfailure_manual_switch),
                                                       Not(test_mode_switch)),
                                  on_activate=Run(SetStatus(waterfailure_manual_switch, 1),
                                                  SetStatus(mainpump, 0),
                                                  SetStatus(uvc_filter, 0),
                                                  SetStatus(heater, 0),
                                                  SetStatus(co2inj, 0),
                                                  SetStatus(alarmtrigger, 1),
                                                  Swap(emailer)),
                                  priority=5,
                                  )

    # Test mode: beep for 2 second for each different GPIO sensor change
    #tstacts_disable = system.actuators[:]
    # tstacts_disable.remove(alarm)
    # tstacts_disable.remove(alarmtrigger)
    tstacts_disable = OfType(AbstractActuator, exclude=[alarm, alarmtrigger])
    #real_sensors = [i for i in system.sensors if isinstance(i, (RpioSensor, ArduinoSensor))]
    real_sensors = OfType(RpioSensor, ArduinoSensor)
    testmodeprog = Program(active_condition=Value(test_mode_switch),
                           update_condition=Or(real_sensors),
                           #on_activate=Run(*[SetValue(i, i) for i in tstacts_disable]),
                           on_activate=SetStatus(tstacts_disable, tstacts_disable),
                           on_update=Run(SetStatus(alarmtrigger, 1), Delay(2, SetStatus(alarmtrigger, 0))),
                           priority=10,
                           )

    sahkokatko_lamps = Program(
        active_condition=Not(electricity_on),
        on_activate=Run(SetStatus(lamp1, 0), SetStatus(lamp2, 0), SetStatus(lamp3, 0),
                        Delay(5 * 60, Run(SetStatus(mainpump, 0), SetStatus(co2pump, 0), SetStatus(co2inj, 0))),
                        Swap(emailer)),
        priority=4,
    )

    waterchange1 = Program(
        active_condition=Value(not_enough_water_in_the_sump),
        on_activate=SetStatus(mainpump, 0),
        priority=5,
    )

    waterchange2 = Program(active_condition=Value(sump_full),
                           on_activate=SetStatus(alarmtrigger, 1)
                           )

    # Write events to a log file
    # logger = LoggingActuator(
    #    targets=[OfType(Sensor, Actuator)],
    #    filename="logi.txt"
    #)

    loginterval = IntervalTimerSensor(interval=60)

    # Triggers can be added manually by using triggers attribute
    # logprog = Program(triggers=[loginterval],
    #                  on_update=Swap(logger),
    #                  )


munsysteemi()

# if __name__ == '__main__':
#    if not load_state():
#        initialize()
#    main()
