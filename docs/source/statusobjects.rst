StatusObjects
=============

.. inheritance-diagram:: automate.statusobject.StatusObject
                         automate.statusobject.AbstractSensor
                         automate.statusobject.AbstractActuator
   :parts: 1


Actuators (:class:`~automate.statusobject.AbstractActuator`) and
sensors (:class:`~automate.statusobject.AbstractSensor`)
are subclassed of :class:`~automate.statusobject.StatusObject`.
The most important property is :attr:`~automate.statusobject.StatusObject.status`,
which may be of various data types, depending of the implementation defined in subclasses.
Type of status is determined by :attr:`~automate.statusobject.StatusObject._status` trait.

There are couple of useful features in StatusObjects that may be used to affect when status
is really changed. These are accessible via the following attributes:

    * :attr:`~automate.statusobject.StatusObject.safety_delay` and :attr:`~automate.statusobject.StatusObject.safety_mode`
      can be used to define a minimum delay between status changes ("safety" ~ some devices might break if changed with big frequency)
    * :attr:`~automate.statusobject.StatusObject.change_delay` and :attr:`~automate.statusobject.StatusObject.change_mode` can be used
      to define a delay which (always) takes place before status is changed.

Here, modes are one of ``'rising'``, ``'falling'``, ``'both'``, default being ``'rising'``. To disable
functionality completely, set corresponding delay parameter to zero. Functions are
described below.

Creating Custom Sensors and Actuators
-------------------------------------

Custom actuators and sensors can be easiliy written based on
:class:`~automate.statusobject.AbstractActuator` and :class:`~automate.statusobject.AbstractSensor`
classes, respectively.

As an example, we will define one of each:

.. literalinclude:: custom_actuators_and_sensors.py

For more examples, look
:mod:`~automate.sensors.builtin_sensors` and
:mod:`~automate.actuators.builtin_actuators`. For more examples, see also :ref:`automate-extensions`,
especially support modules for Arduino and Raspberry Pi IO devices)

StatusObject Definition
-----------------------

.. autoclass:: automate.statusobject.StatusObject
   :members:

Sensor Baseclass Definition
---------------------------

.. inheritance-diagram:: automate.statusobject.AbstractSensor
   :parts: 1

.. autoclass:: automate.statusobject.AbstractSensor
   :members:

Actuator Baseclass Definition
-----------------------------

.. inheritance-diagram:: automate.statusobject.AbstractActuator
   :parts: 1

.. autoclass:: automate.statusobject.AbstractActuator
   :members:
