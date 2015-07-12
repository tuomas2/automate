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

.. code-block:: python

   # imports from your own library that you are using to define your sensor & actuator
   from mylibrary import (setup_data_changed_callback, fetch_data_from_my_datasource, initialize_my_actuator_device,
                          change_status_in_my_actuator_device)

   class MySensor(AbstractSensor):
       """
       Let us assume that you have your own library which has a status that you want to track
       in your Automate program.
       """
       # define your status data type
       _status = CBool
       def setup(self):
           setup_my_datasource()
           # we tell our library that update_status need to be called when status is changed
           # We could use self.set_status directly, if library can pass new status as an argument.
           setup_data_changed_callback(self.update_status)
       def update_status(self):
           # fetch new status from your datasource (this function is called by your library)
           self.status = fetch_data_from_your_datasource()
       def cleanup(self):
           # define this if you need to clean things up when program is stopped
           pass

   class MyActuator(AbstractActuator):
       # define your status data type. Transient=True is a good idea because
       # actuator status is normally determined by other values (sensors & programs etc)
       _status = CFloat(transient=True)
       def setup(self):
           initialize_my_actuator_device()
       def _status_changed(self):
           chagnge_status_in_my_actuator_device(self.status)

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
