from automate.extensions.arduino.arduino_sensors import ArduinoAnalogSensor

from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService
from automate.extensions.webui import WebService


class PlantLamp(System):
    fan = ArduinoDigitalActuator(pin=3)
    light = ArduinoDigitalActuator(pin=8)

    light_intensity = ArduinoAnalogSensor(pin=3)


s = PlantLamp(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=30000, # every 30 seconds
            home_address=1,
            device_address=50,
            virtualwire_rx_pin=10,
            virtualwire_tx_pin=11,
            keep_alive=True,
            #wakeup_pin=2,
            virtualwire_speed=4,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
