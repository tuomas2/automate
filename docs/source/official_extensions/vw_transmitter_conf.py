class ArduinoSystem(System):
    digital_sensor1 = ArduinoDigitalSensor(pull_up_resistor=True, pin=2)
    digital_sensor2 = ArduinoDigitalSensor(pull_up_resistor=True, pin=3)
    analog_sensor1= ArduinoAnalogSensor(pin=0)
    analog_sensor2= ArduinoAnalogSensor(pin=1)

s = ArduinoSystem(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=2000,
            home_address=1,
            device_address=1,
            virtualwire_tx_pin=11,
            virtualwire_ptt_pin=12,
        ),
    ],
)