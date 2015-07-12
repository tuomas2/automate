Automate System
===============

Introduction
------------

:class:`automate.system.System` encapsulates the state machine parts into single object. It has already been
explained how to use System. Here we will go further into some details.


.. _groups:

Groups
------


In Automate system, it is possible to group objects by putting them to Groups. Grouping helps organizing
objects in code level as well as in GUIs (:ref:`automate-webui` etc.).

Here is an example::

    class MySystem(System):
        class group1(Group):
            sensor1 = UserBoolSensor()
            sensor2 = UserBoolSensor()

        class group2(Group):
            sensor3 = UserBoolSensor()
            sensor4 = UserBoolSensor()

By adding SystemObject to a group, will assign it a tag corresponding to its groups class name. I.e. here,
``sensor1`` and ``sensor2`` will get tag *group:group1* and ``sensor3`` and ``sensor4`` will get tag *group:group2*.

System has single namespace dictionary that contains names of all objects. That implies
that objects in different groups may not have same name.

.. _state-saving:

System State Saving and Restoring via Serialization
---------------------------------------------------

If System state is desired to be loaded later from periodically auto-saved state dumps,
system can be instantiated via :meth:`~automate.system.System.load_or_create` as follows::

    my_system_instance = MySystem.load_or_create('my_statedump.dmp')

Then system state will be saved periodically (by default, once per 30 minutes) by
:class:`~automate.services.statussaver.StatusSaverService`, which is automatically loaded
service (see :ref:`services`). If you desire to change
interval, you need to explicitly define
:attr:`~automate.services.statussaver.StatusSaverService.dump_interval`
as follows::

    status_saver = StatusSaverService(dump_interval=10) # interval in seconds
    my_system_instance = MySystem.load_or_create('my_statedump.dmp', services=[status_saver])


SystemObject
------------

.. inheritance-diagram:: automate.system.SystemObject
   :parts: 1

:class:`~automate.systemobject.SystemObject` is baseclass for all objects that may be used within
:class:`~automate.system.System` (most importantly,
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

System Class Definition
-----------------------

.. autoclass:: automate.system.System
   :members:


SystemObjects Class Definition
------------------------------

.. autoclass:: automate.systemobject.SystemObject
   :members:

