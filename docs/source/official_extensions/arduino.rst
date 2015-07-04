.. _automate-arduino:

Arduino Support for Automate
============================

Github URL: http://github.com/tuomas2/automate-arduino

Introduction
------------

This extension provides interface to Arduino devices via `pyFirmata library <https://github.com/tino/pyFirmata>`_.

Example application
-------------------

This example application sets up couple of analog and digital Arduino Sensors and Actuators.
It also introduces Servo actuator with :class:`~automate.actuators.builtin_actuators.ConstantTimeActuator`,
which functions such a way that if value of ``a1`` changes, the value of ``servo`` will change smoothly
within given time interval.

.. literalinclude:: arduino_example.py


Class definitions
-----------------

Service
^^^^^^^

.. autoclass:: automate_arduino.ArduinoService
   :members:

Sensors
^^^^^^^

.. autoclass:: automate_arduino.AbstractArduinoSensor
   :members:

.. autoclass:: automate_arduino.ArduinoDigitalSensor
   :members:

.. autoclass:: automate_arduino.ArduinoAnalogSensor
   :members:


Actuators
^^^^^^^^^

.. autoclass:: automate_arduino.AbstractArduinoActuator
   :members:

.. autoclass:: automate_arduino.ArduinoDigitalActuator
   :members:

.. autoclass:: automate_arduino.ArduinoPWMActuator
   :members:

.. autoclass:: automate_arduino.ArduinoServoActuator
   :members:
