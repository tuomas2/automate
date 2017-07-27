class ArduinoSystem(System):
    ubool = UserBoolSensor()
    ufloat1 = UserFloatSensor(value_min=0, value_max=1)

    remote_actuator = ArduinoRemoteDigitalActuator(
        device=3, pin=13,
        on_update=SetStatus('remote_actuator', 'ubool'))

    remote_pwm = ArduinoRemotePWMActuator(
        device=3, pin=5,
        on_update=SetStatus('remote_pwm', 'ufloat1'))



s = ArduinoSystem(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=2000,
            home_address=1,
            device_address=4,
            virtualwire_tx_pin=11,
            virtualwire_ptt_pin=12,
        ),
        WebService(read_only=False),
    ],
)
