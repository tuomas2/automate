.. _automate-arduino:

Arduino Support for Automate
============================

Introduction
------------

This extension provides interface to Arduino devices via `pyFirmata library <https://github.com/tino/pyFirmata>`_.

Installation
------------

Install extras::

    pip install automate[arduino]

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

.. autoclass:: automate.extensions.arduino.ArduinoService
   :members:

Sensors
^^^^^^^

.. autoclass:: automate.extensions.arduino.AbstractArduinoSensor
   :members:

.. autoclass:: automate.extensions.arduino.ArduinoDigitalSensor
   :members:

.. autoclass:: automate.extensions.arduino.ArduinoAnalogSensor
   :members:


Actuators
^^^^^^^^^

.. autoclass:: automate.extensions.arduino.AbstractArduinoActuator
   :members:

.. autoclass:: automate.extensions.arduino.ArduinoDigitalActuator
   :members:

.. autoclass:: automate.extensions.arduino.ArduinoPWMActuator
   :members:

.. autoclass:: automate.extensions.arduino.ArduinoServoActuator
   :members:
