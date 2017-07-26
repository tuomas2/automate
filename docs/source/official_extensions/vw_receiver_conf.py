s = System(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=2000,
            home_address=1,
            device_address=3,
            virtualwire_rx_pin=11,
        ),
    ],
)