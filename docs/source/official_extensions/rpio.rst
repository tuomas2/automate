.. _automate-rpio:

Raspberry Pi GPIO Support for Automate
======================================

Github URL: http://github.com/tuomas2/automate-rpio

Introduction
------------

This extension provides interface to Raspberry Pi GPIO via RPIO library. `RPIO library <http://pythonhosted.org/RPIO/>`_.

Example application
-------------------

This simple example application sets up simple relation between input pin ``button`` in port 22 and
output pin ``light`` in port 23. If for a button is attached in ``button``, pushing it down
will light the led, that is attached to ``light``.

.. literalinclude:: gpio_example.py


Class definitions
-----------------

Service
^^^^^^^

.. autoclass:: automate_rpio.RpioService
   :members:


Sensors
^^^^^^^

.. autoclass:: automate_rpio.RpioSensor
   :members:

.. autoclass:: automate_rpio.RpioSensor
   :members:

Actuators
^^^^^^^^^

.. autoclass:: automate_rpio.RpioActuator
   :members:

.. autoclass:: automate_rpio.TemperatureSensor
   :members:

.. autoclass:: automate_rpio.RpioPWMActuator
   :members:

