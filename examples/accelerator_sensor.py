from automate import *
from automate.extensions.arduino import ArduinoAnalogSensor, ArduinoService
from automate.extensions.webui import WebService


val_list = []
count = 0
def plot(x, y, z):
    global count
    val_list.append((x, y, z))
    print('value', count, x, y, z)
    count += 1
    if count % 1000 == 0:
        print('writing to file')
        with open('dump.txt', 'w') as f:
            for i, (x, y, z) in enumerate(val_list):
                f.write(f'{i} {x} {y} {z}\n')


class Motion(System):
    x = ArduinoAnalogSensor(service=0, pin=0,
                            active_condition=Value(True),
                            update_condition=Value(True),
                            on_update=Func(plot, 'x', 'y', 'z'),
                            exclude_triggers={'y', 'z'}
                            )
    y = ArduinoAnalogSensor(service=0, pin=1)
    z = ArduinoAnalogSensor(service=0, pin=2)


s = Motion(
    services=[
        ArduinoService(
            device="/dev/ttyUSB0",
            device_type='arduino"',
            sample_rate=100,
        ),
        WebService(),
    ],
)