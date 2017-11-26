from automate.extensions.arduino.arduino_actuators import ArduinoRemoteDigitalActuator, \
    ArduinoRemotePWMActuator
from automate.extensions.arduino.arduino_sensors import ArduinoAnalogSensor, \
    ArduinoRemoteAnalogSensor

from automate import *
from automate.extensions.arduino import ArduinoDigitalActuator, ArduinoPWMActuator, \
    ArduinoService
from automate.extensions.webui import WebService


class PlantLamp(System):
    fan_set = UserBoolSensor(
                              on_update=SetStatus('fan', 'fan_set')
                              )

    light_set = UserBoolSensor(
                              on_update=Run(
                                  SetStatus('light', 'light_set'),
                              )
                              )

    fan = ArduinoRemoteDigitalActuator(device=50, pin=3)

    light = ArduinoRemoteDigitalActuator(device=50, pin=8)
    tester = ArduinoRemoteDigitalActuator(device=50, pin=13)

    light_intensity = ArduinoRemoteAnalogSensor(device=50, pin=3)



s = PlantLamp(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            sample_rate=30000, # every 30 seconds
            home_address=1,
            device_address=51,
            virtualwire_rx_pin=10,
            virtualwire_tx_pin=11,
            keep_alive=True,
            #wakeup_pin=2,
            virtualwire_speed=4,
            log_level=logging.DEBUG,
        ),
        TextUIService(),
        WebService(read_only=False),
    ],
)
