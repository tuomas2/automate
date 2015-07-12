from automate import *

class MySystem(System):
    # HW swtich connected Raspberry Pi GPIO port 1
    hardware_switch = RpioSensor(port=1)
    # Switch that is controllable, for example, from WEB interface
    web_switch = UserBoolSensor(tags=['user'])
    # Lamp relay that switches lamp on/off, connected to GPIO port 2
    lamp = RpioActuator(port=2)
    # Program that controls the system behaviour
    program = Program(
        active_condition = Or('web_switch', 'hardware_switch'),
        on_activate = SetStatus('lamp', True)
    )

# To view UML diagram, we need to set up PlantUMLService. Here we will use
# plantuml.com online service to render the UML graphics.
plantuml_service = PlantUMLService(url='http://www.plantuml.com/plantuml/svg/')
web_service = WebService(
                    read_only=False,
                    default_view='plantuml',
                    http_port=8085,
                    http_auth = ('myusername', 'mypassword'),
                    user_tags = ['user'],
                    )

# Just to give example of slave feature, let's open another server instance
# at port 8086.
slave = WebService(
                   http_port=8086,
                   slave=True,
                   )

my_system = MySystem(services=[plantuml_service, web_service, slave])
