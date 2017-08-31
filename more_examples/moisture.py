from automate import *
from automate.extensions.arduino import ArduinoAnalogSensor, ArduinoService
from automate.extensions.webui import WebService


class Moisture(System):
    meas = ArduinoAnalogSensor(pin=3)

if __name__ == '__main__':
    s = Moisture(
        services=[
            WebService(),
            ArduinoService(
                sample_rate=8000,
                virtualwire_rx_pin=11),
        ]
    )
