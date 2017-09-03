from automate.extensions.arduino.arduino_actuators import ArduinoRemoteDigitalActuator, \
    ArduinoRemotePWMActuator
from automate.extensions.arduino.arduino_sensors import ArduinoAnalogSensor, \
    ArduinoRemoteAnalogSensor

from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService
from automate.extensions.webui import WebService


class PlantLamp(System):
    fan_set = UserFloatSensor(value_min=0, value_max=1,
                              on_update=SetStatus('fan', 'fan_set')
                              )

    light_set = UserBoolSensor(
                              on_update=SetStatus('light', 'light_set')
                              )

    fan = ArduinoRemotePWMActuator(device=50, pin=9)
    light = ArduinoRemoteDigitalActuator(device=50, pin=8)

    light_intensity = ArduinoRemoteAnalogSensor(device=50, pin=3)


s = PlantLamp(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            home_address=1,
            device_address=51,
            virtualwire_rx_pin=10,
            virtualwire_tx_pin=11,
            keep_alive=True,
            #wakeup_pin=2,
            virtualwire_speed=7,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
