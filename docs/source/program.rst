
Programming Automate Objects
============================

.. _automate-programs:

Programs
--------

Program features are defined in :class:`~automate.program.ProgrammableSystemObject` class.
:class:`~automate.program.Program`, :class:`~automate.program.DefaultProgram` and
:class:`~automate.statusobject.StatusObject` classes are subclassed
from :class:`~automate.program.ProgrammableSystemObject`, as can be seen in the following
inheritance diagram.


.. inheritance-diagram:: automate.program.Program
                         automate.program.DefaultProgram
                         automate.statusobject.StatusObject
                         automate.statusobject.AbstractSensor
                         automate.statusobject.AbstractActuator
   :parts: 1

Programs are used to define the logic on which system operates. Program behavior is determined by the conditions
(:attr:`~automate.program.ProgrammableSystemObject.active_condition`,
:attr:`~automate.program.ProgrammableSystemObject.update_condition`) and actions
(:attr:`~automate.program.ProgrammableSystemObject.on_activate`,
:attr:`~automate.program.ProgrammableSystemObject.on_update`,
:attr:`~automate.program.ProgrammableSystemObject.on_deactivate`),
that are of :class:`~automate.callable.AbstractCallable`
type. Callables are special objects that are used to implement the actual programming of Automate program objects
(see :ref:`callables`). There are many special Callable classes to perform different operations
(see :ref:`builtin-callables`) and it is also easy to develop your own Callables
(see :ref:`deriving-callables`).

All Sensors and Actuators that affect the return value of a condition callable,
are :attr:`~automate.callable.AbstractCallable.triggers` of a Callable. All actuators (and writeable sensors) that
a callable may change, are :attr:`~automate.callable.AbstractCallable.targets`. Whenever any of the
triggers status change, programs
conditions are automatically updated and actions are taken if appropriate condition evaluates
as ``True``.

Actions and conditions are used as follows. Programs can be either active or inactive depending on
:attr:`~automate.program.ProgrammableSystemObject.active_condition`. When program actives
(i.e. active_condition changes to ``True``),
:attr:`~automate.program.ProgrammableSystemObject.on_activate`
action is called. When program deactivates,
:attr:`~automate.program.ProgrammableSystemObject.on_deactivate`,
action is called, correspondingly.
When program is active, its targets can be continuously manipulated by
:attr:`~automate.program.ProgrammableSystemObject.on_update`
callable, which
is called whenever update_condition evaluates as ``True``.

Actuator Status Manipulation
----------------------------

Program can control status
of one or more actuators. Programs manipulate Actuator statuses the following way:

* One or more programs can control state of the same Actuator. Each program has
  :attr:`~automate.program.ProgrammableSystemObject.priority` (floating point number), so that
  the actual status of Actuator is determined
  by program with highest priority
* If highest priority program deactivates, the control of Actuator status is moved
  to the the second-highest priority active program.
* If there are no other Program, each Actuator has also one DefaultProgram, which then
  takes over Actuator control.

The following example application illustrates the priorities::

    from automate import *
    class MySystem(System):
        low_prio_prg = UserBoolSensor(priority=-5,
                                      active_condition=Value('low_prio_prg'),
                                      on_activate=SetStatus('actuator', 1.0),
                                      default=True,
                                      )
        med_prio_prg = UserBoolSensor(priority=1,
                                      active_condition=Value('med_prio_prg'),
                                      on_activate=SetStatus('actuator', 2.0),
                                      default=True,
                                      )
        high_prio_prg = UserBoolSensor(priority=5,
                                      active_condition=Value('high_prio_prg'),
                                      on_activate=SetStatus('actuator', 3.0),
                                      default=True,
                                      )
        inactive_high_prio_prg = UserBoolSensor(priority=6,
                                      active_condition=Value('inactive_high_prio_prg'),
                                      on_activate=SetStatus('actuator', 4.0),
                                      default=False,
                                      )

        actuator = FloatActuator()

    ms = MySystem(services=[WebService()])

.. image:: images/program.svg

In this application, four programs (three manually defined programs and :class:`~automate.program.DefaultProgram`
``dp_actuator``) are active for actuator.
The actual status of actuator (now: ``3.0``) is determined by highest priority program.
If ``high_prio_prog`` goes inactive (i.e. if its
status is changed to ``False``)::

    high_prio_prg.status = False

the status is then determined by ``med_prio_prg`` (=> ``2.0``). And so on. All the active programs
for actuator are visible in UML diagram.
Red arrow shows the dominating program, blue arrows show the other non-dominating active programs and gray arrows
show the inactive programs that have the actuator as a target (i.e. if they are activated, they will manipulate
the status of the actuator). ``low_prio_prg`` can never manipulate actuator status as its priority is lower than
default program ``dp_actuator`` priority.

Program Features
----------------

Program features are defined in ``ProgrammableSystemObject`` class. Its definition is as follows:

.. note::
    Unfortunately, due to current Sphinx autodoc limitation, all trait types are displayed in this
    documentation as ``None``. For the real trait types, please see the source fode.

.. autoclass:: automate.program.ProgrammableSystemObject
   :members:
