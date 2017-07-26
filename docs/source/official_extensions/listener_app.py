class ArduinoSystem(System):
    digi1 = ArduinoRemoteDigitalSensor(dev=0, source_device=1, pin=2)
    digi2 = ArduinoRemoteDigitalSensor(dev=0, source_device=1, pin=3)
    analog1 = ArduinoRemoteAnalogSensor(dev=0, source_device=1, pin=0)
    analog2 = ArduinoRemoteAnalogSensor(dev=0, source_device=1, pin=1)


s = ArduinoSystem(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=2000,
            home_address=1,
            device_address=2,
            virtualwire_rx_pin=10,
        ),
    ],
)