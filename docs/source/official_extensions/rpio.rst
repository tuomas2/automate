.. _automate-rpio:

Raspberry Pi GPIO Support for Automate
======================================

Introduction
------------

This extension provides interface to Raspberry Pi GPIO via RPIO library. `RPIO library <http://pythonhosted.org/RPIO/>`_.

Installation
------------

Install extras::

    pip install automate[raspberrypi]

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

.. autoclass:: automate.extensions.rpio.RpioService
   :members:


Sensors
^^^^^^^

.. autoclass:: automate.extensions.rpio.RpioSensor
   :members:

.. autoclass:: automate.extensions.rpio.RpioSensor
   :members:

Actuators
^^^^^^^^^

.. autoclass:: automate.extensions.rpio.RpioActuator
   :members:

.. autoclass:: automate.extensions.rpio.TemperatureSensor
   :members:

.. autoclass:: automate.extensions.rpio.RpioPWMActuator
   :members:

