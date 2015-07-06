.. _callables:

Callables
=========

Introduction
------------

Callables are used like a small *programming language* to define the programming logic within the
Automate system. All classes derived from :class:`~automate.program.ProgrammableSystemObject` have five
attributes that accept Callable type objects:

 * Conditions

   * :attr:`~automate.program.ProgrammableSystemObject.active_condition`
   * :attr:`~automate.program.ProgrammableSystemObject.update_condition`

 * Actions

   * :attr:`~automate.program.ProgrammableSystemObject.on_activate`
   * :attr:`~automate.program.ProgrammableSystemObject.on_update`
   * :attr:`~automate.program.ProgrammableSystemObject.on_deactivate`

Conditions determine *when* and actions, correspondingly, *what* to do.

Actions are triggered by *triggers* that are Sensors and Actuators. Triggers are collected
from Callables (conditions and actions) automatically, and their status changes are subscribed and followed
automatically by a
:class:`~automate.program.ProgrammableSystemObject`. Thus, condition statuses are evaluated automatically, and
actions are executed based on condition statuses.

Let us take a look at a small example that uses conditions and actions:


.. uml::
    @startuml
    skinparam state {
    BackGroundColor<<actuator>> #FFCCFF
    BackGroundColor<<program>> #FFFFCC
    BackGroundColor<<sensor>> #CCFFCC
    }
    state "prog" as prog <<program>>
    prog: Program
    prog: Status: True
    prog: Priority: 1
    periodical -[#009933]-> prog
    active_switch -[#009933]-> prog
    prog -[#FF0000]-> target_actuator
    state "target_actuator" as target_actuator <<actuator>>
    target_actuator: IntActuator
    target_actuator: prog :: 7.0
    target_actuator: dp_target_actuator :: 0
    state "periodical" as periodical <<sensor>>
    periodical: IntervalTimerSensor
    periodical: Status: 1.0
    state "active_switch" as active_switch <<sensor>>
    active_switch: UserBoolSensor
    active_switch: Status: True
    @enduml

.. code-block:: python

   from automate import *

   class CounterClock(System):
      active_switch = UserBoolSensor()
      periodical = IntervalTimerSensor(interval=1)

      target_actuator = IntActuator()

      prog = Program(
                 active_condition = Value(active_switch),
                 on_activate = SetStatus(target_actuator, 0),
                 on_update = SetStatus(target_actuator,
                                       target_actuator + 1),
                 triggers = [periodical],
                 exclude_triggers = [target_actuator],
                 )

   s = CounterClock(services=[WebService(read_only=False)])

When user has switched ``active_switch`` sensor to ``True``, this simple program will start adding +1 to target_actuator value every
second. Because ``periodical`` is not used as a trigger in any action/condition, we need to explicitly define it as a
trigger with triggers attribute. Correspondingly, ``target_actuator`` is automatically collected as prog's trigger (because
it is the second argument of SetStatus), so we need to explicitly exclude it with ``exclude_triggers`` attribute.

.. tip::

    Try the code yourself! Just cpaste the code into your IPython shell and go to http://localhost:8080 in your browser!
    Screenshot:

    .. image:: images/counter_app.png

.. _deriving-callables:

Deriving Custom Callables
-------------------------

A collection of useful Callables is provided by :mod:`~automate.callables.builtin_callables` module.
It is also easy to derive custom callables from :class:`~automate.callable.AbstractCallable` baseclass.
For most cases it is enough to re-define :meth:`~automate.callable.AbstractCallable.call` method.

If Callable utilizes threads (like
:class:`~automate.callables.builtin_callables.Delay`,
:class:`~automate.callables.builtin_callables.WaitUntil` and
:class:`~automate.callables.builtin_callables.While`)
and continues as an background process after returning from call method, it is also necessary
to define :meth:`~automate.callable.AbstractCallable.cancel` that notifies threads that their processing
must be stopped. These threaded Callables can store their threads and other information in
:attr:`~automate.callable.AbstractCallable.state` dictionary, which stores information per
caller Program. Per-caller state information is fetched via
:meth:`~automate.callable.AbstractCallable.get_state`. After data is no longer needed, it must be cleared with
:meth:`~automate.callable.AbstractCallable.del_state` method.

Arguments given to Callable are stored in
:attr:`~automate.callable.AbstractCallable._args`  and keyword arguments in
:attr:`~automate.callable.AbstractCallable._kwargs`. There are the following shortcuts that may
be used:
:attr:`~automate.callable.AbstractCallable.obj`,
:attr:`~automate.callable.AbstractCallable.value` and
:attr:`~automate.callable.AbstractCallable.objects`. When accessing these, it is necessary (almost) always
to use :meth:`~automate.callable.AbstractCallable.call_eval` method, which evaluates concurrent status value
out of Callable, StatusObject, or string that represents name of an object residing in System namespace.
See more in the following section.


Trigger and Target Collection
-----------------------------

Triggers and targets are automatically collected from Callables recursively.
All Callable types can specify which arguments are considered as triggers and which
are considered as targets, by defining
:meth:`~automate.callable.AbstractCallable._give_triggers` and
:meth:`~automate.callable.AbstractCallable._give_targets`, correspondingly.

As a general rule, Callable should not consider criteria conditions as triggers
(for example the conditions of
:class:`~automate.callables.builtin_callables.If`,
:class:`~automate.callables.builtin_callables.Switch`
etc).

Referring to Other Objects in Callables
---------------------------------------

Various system objects can be referred either by name (string), or by object references.
Name is preferred, because it allows to refer to objects that are defined in different
scopes (i.e. those that are defined either in :ref:`groups` or later in the code).

If desired, automatic name referencing can be also disabled by setting
:attr:`~automate.system.System.allow_name_referencing` False. Then it is possible
to refer to other objects by using special construct Object('name').

All variables passed to Callables are/must be evaluated through
:meth:`~automate.callable.AbstractCallable.call_eval` method, i.e.
if Callables are used as arguments, they are evaluated by their
:meth:`~automate.callable.AbstractCallable.call` method
and :class:`~automate.statusobject.StatusObject`'s status attribute is used, respectively.

Callable Abstract Base Class definition
---------------------------------------

Callable classes are are subclassed of :class:`~automate.callable.AbstractCallable`.

.. autoclass:: automate.callable.AbstractCallable
   :members:
   :private-members:


