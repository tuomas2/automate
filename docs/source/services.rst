.. _services:

Services
========

Introduction
------------

There are two kinds of *Services* in Automate: *UserServices* and *SystemServices*.

*SystemServices* are mainly designed to implement a practical way of writing an interface between your
custom SystemObjects and their corresponding resources (devices for example). For example,
:class:`~automate.extensions.rpio.RpioService`
provide access to Raspberry Pi GPIO pins for
:class:`~automate.extensions.rpio.RpioActuator` and
:class:`~automate.extensions.rpio.RpioSensor` objects,
and ArduinoService, correspondingly, provides access to Arduino devices for ArduinoActuator and ArduinoSensors.
(Arduino and RPIO support are provided by extensions, see :ref:`automate-extensions`).

*UserServices*, on the other hand, provide user interfaces to the system. For example,
:class:`~automate.extensions.webui.WebService`
provides access to the system via web browser,
:class:`~automate.services.textui.TextUIService`
via *IPython* shell and
:class:`~automate.extensions.rpc.RpcService`
via XmlRPC (remote procedure call) interface for other applications.

If not automatically loaded (services with :attr:`~automate.service.AbstractService.autoload` set to ``True``),
they need to be instantiated (contrary to :class:`~automate.systemobject.SystemObject`)
outside the System, and given in the initialization of the system (:attr:`~automate.system.System.services`).
For example of initialization and configuring of
:class:`~automate.extensions.webui.WebService`, see :ref:`hello-world`.

Services Class Definitions
--------------------------

.. autoclass:: automate.service.AbstractService
   :members:

.. autoclass:: automate.service.AbstractUserService
   :members:

.. autoclass:: automate.service.AbstractSystemService
   :members:

Builtin Services
----------------

.. autoclass:: automate.services.logstore.LogStoreService
   :members:

.. autoclass:: automate.services.statussaver.StatusSaverService
   :members:

.. autoclass:: automate.services.plantumlserv.PlantUMLService
   :members:

.. autoclass:: automate.services.textui.TextUIService
   :members:

