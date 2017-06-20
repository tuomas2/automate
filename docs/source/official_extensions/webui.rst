.. _automate-webui:

Web User Interface for Automate
===============================

Introduction
------------

Automate Web UI extension provides easy to use approach to monitoring and modifying
Automate system and its components. Features:

- Displayed data updated in real time via Websocket
- Responsive design (using `Bootstrap <http://getbootstrap.com/>`_ CSS & JS library), suitable for
  mobile and desktop use.
- Optional authentication
- Read-only and read-write modes.

  - Read-only mode allows only monitoring (default)
  - Read-write mode allows modifying the System by:

    - adding new Actuators / Sensors / Programs
    - modifying existing Actuators / Sensors / Programs
    - Quick editing of user-editable sensors from main views

- HTTP and secured HTTPS servers supported (powered by built in `Tornado Web Server <www.tornadoweb.org/>`_)

Main features are illustrated with a few screenshots:

Installation
------------

Install extras::

    pip install automate[web]

Main view
^^^^^^^^^

In main view you can observe actuator and sensor statuses in real time, and also easily access
user-editable sensor statuses. Clicking object name will give more details of the selected item
as well as 'edit' button. (only in read-write mode).

.. figure:: images/main_view.png

Edit view
^^^^^^^^^

In edit view you can edit almost all the attributes of the objects that are in the system.
You can also create new ones.

.. figure:: images/edit_view.png

UML view
^^^^^^^^^

In UML view you can see nice UML diagram of the whole system. To enable UML diagram, you need to set
up :class:`~automate.services.builtin_services.PlantUMLService`.

.. figure:: images/uml_view.png

Console  view
^^^^^^^^^^^^^

In console view you can see the log as well as type commands same way as in IPython shell.

.. figure:: images/shell_view.png


Example application using Web UI
--------------------------------

This is extended example of the :ref:`hello-world`, that opens two web services, one for port 8085 and another
in 8086. It will go to UML view by default and in "User defined" -view you will see only ``web_switch``.

.. literalinclude:: webui_example.py

.. tip::
   Try to run the code in your IPython shell by copying & pasting it with ``cpaste`` command!

WebService class definition
---------------------------

.. autoclass:: automate_webui.WebService
   :members:

