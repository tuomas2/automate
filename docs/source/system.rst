Automate System
===============

Introduction
------------

System encapsulates the state machine parts into single object. It has already been
explained how to use System. Here we will go further into some details.

System Class Definition
-----------------------

.. autoclass:: automate.system.System
   :members:


.. _groups:

Groups
------


In a Automate system, it is possible to group objects by putting them to Groups. Grouping helps organizing
objects in code level as well as in GUIs (WEB UI etc.).

Here is an example::

    class MySystem(System):
        class group1(Group):
            sensor1 = UserBoolSensor()
            sensor2 = UserBoolSensor()

        class group2(Group):
            sensor3 = UserBoolSensor()
            sensor4 = UserBoolSensor()

By adding SystemObject to a group, will assign it a tag corresponding to its groups class name. I.e. here,
*sensor1* and *sensor2* will get tag *group:group1* and sensor3 and sensor4 will get tag *group:group2*.

System namespace
----------------

System has single namespace that contains names of all objects. That implies
that objects in different groups_ may not have same name.

.. autoclass:: automate.namespace.Namespace
   :members:


SystemObject
------------

.. inheritance-diagram:: automate.system.SystemObject
   :parts: 1

SystemObject is baseclass for all objects that may be used within System (most importantly,
Sensors, Actuators and Programs).

Due to multiple inheritance, many SystemObjects,
such as Sensors (:class:`~automate.statusobject.AbstractSensor`),
Actuators (:class:`~automate.statusobject.AbstractActuator`), and
Programs (:class:`~automate.program.Program`) can act in *multiple roles*,
in addition to their primary role, as follows:

* Sensors and actuators can always be used also as a program i.e. they may have conditions
  and action callables defined, because they derive from :class:`~automate.program.ProgrammableSystemObject`.
* Both Actuators and Sensors can be used as *triggers* in Callables and via them in Programs
* Also plain Programs can be used as a Sensor. Then its activation status (boolean) serves as Sensor status.

Sensors and Programs do not have Actuator properties (i.e. per-program statuses), but
Sensor status can still be set/written by a Program, similarly to actuators with
:attr:`~automate.statusobject.AbstractActuator.slave` attribute set to True.

SystemObjects Class Definition
------------------------------

.. autoclass:: automate.systemobject.SystemObject
   :members:



