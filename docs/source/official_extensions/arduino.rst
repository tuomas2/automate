.. _automate-arduino:

Arduino Support for Automate
============================

Introduction
------------

This extension provides interface to Arduino devices via `pyFirmata library <https://github.com/tino/pyFirmata>`_.
You can use either StandardFirmata or preferrably `AutomateFirmata <https://github.com/tuomas2/AutomateFirmata>`_,
which offers additional features that can be used with Automate. Please use corresponding version
of AutomateFirmata from `releases -page <https://github.com/tuomas2/AutomateFirmata/releases>`_.
I have tested this module with Arduino Pro Mini compatible boards but it should work with
others too.

Example application
-------------------

This example application sets up couple of analog and digital Arduino Sensors and Actuators.
It also introduces Servo actuator with :class:`~automate.actuators.builtin_actuators.ConstantTimeActuator`,
which functions such a way that if value of ``a1`` changes, the value of ``servo`` will change smoothly
within given time interval.

.. literalinclude:: arduino_example.py

VirtualWire wireless communication
----------------------------------

VirtualWire enables communication between two Arduinos with very cheap radio frequency (RF)
transmitters&receivers. For more information about VirtaualWire, see for example
`this link <https://www.pjrc.com/teensy/td_libs_VirtualWire.html>`_.
It is possible to make Automate communicate with remote Arduinos via
VirtualWire. How to do this:

To configure independent Arduino transmitter module with Automate:

 1. Flash AutomateFirmata to your Arduino
 2. Make simple Automate application to configure Arduino that configures which
    pin values you are interested in being transmitted via VirtualWire, something like this:

.. literalinclude:: vw_transmitter_conf.py

Here you need to connect your RF transmitter device to digital pin 11.
With some transmitter devices you might save some power by using push to talk
(PTT) pin 12 to power on/off your transmitter device. This will configure
your module to transmit values from analog pins 0 and 1, and
digital pins 2 and 3. Now you can disconnect Arduino's serial interface and
it will work independently. When running this configuration application,
Arduino stores configuration to its EEPROM memory, such that after booting
you don't need any more configuration. AutomateFirmata also saves power when in
transmitter mode, so you can implement battery powered sensors that consume very
little battery.

To listen these events, you need another Arduino that is connected permanently to your
Automate computer:

.. literalinclude:: listener_app.py

Notice that here you need to configure ``device`` attribute same as device_address
that you configured above. Also ``home_address`` needs to be same between all Arduino
devices that you configure in your system.

You can also configure independent receiver module:

.. literalinclude:: vw_receiver_conf.py

This is all that is needed for receiver. What this does is sets ``home_address``, ``device_address``
and ``virtualwire_tx_pin`` in your Arduino receiver device correctly. You must connect
your RF receiver device to digital pin 11. Now you can control this device remotely
like this:

.. literalinclude:: transmitter_app.py

Here, you must configure your RF transmitter to digital pin 11.

Class definitions
-----------------

Service
^^^^^^^

.. autoclass:: automate.extensions.arduino.ArduinoService
   :members:

Sensors
^^^^^^^

.. automodule:: automate.extensions.arduino.arduino_sensors
   :members:


Actuators
^^^^^^^^^
.. automodule:: automate.extensions.arduino.arduino_actuators
   :members:

