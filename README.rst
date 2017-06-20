.. image:: https://travis-ci.org/tuomas2/automate.svg?branch=master
   :target: https://travis-ci.org/tuomas2/automate
   :alt: Travis CI Status

.. image:: https://coveralls.io/repos/github/tuomas2/automate/badge.svg?branch=master
   :target: https://coveralls.io/github/tuomas2/automate?branch=master
   :alt: Coverage Status

.. image:: https://readthedocs.org/projects/python-automate/badge/?version=master
   :target: https://readthedocs.org/projects/python-automate/?badge=master
   :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/automate.svg
   :target: https://pypi.python.org/pypi/automate

.. image:: https://img.shields.io/pypi/pyversions/automate.svg
   :target: https://pypi.python.org/pypi/automate

.. image:: https://img.shields.io/badge/licence-GPL-blue.svg
   :target: https://github.com/tuomas2/automate/blob/master/LICENSE.txt


Automate
========

- Github URL: http://github.com/tuomas2/automate
- Read full documentation at http://python-automate.readthedocs.org/

Automate is a general purpose automatization library for Python.
Its objective is to offer convenient and robust object-oriented programming
framework for complex state machine systems. Automate can be used to design
complex automation systems, yet it is easy to learn and fun to use. It was
originally developed with home robotics/automatization projects in mind,
but is quite general in nature and one could find applications from various
fields that could take advantage of Automate. Automate can be embedded
in other Python software as a component, which runs its operations in
its own threads.

Highlights:
-----------

* Supported hardware:

  * Raspberry Pi GPIO input/output ports
  * Arduino analog and digital input/output ports (via `pyFirmata <https://github.com/tino/pyFirmata>`_ library)
  * Easy to write extensions to support other hardware

* System state saving and restoring via serialization
* Intelligent design:

  * Comprehensively tested via ``py.test`` unit/integration tests
  * Takes advantage of `Traits <http://traits.readthedocs.org/en/4.6.0/>`_ library, especially its
    notification system.
  * `IPython <http://ipython.org>`_ console to monitor, modify and control system on-the-fly
  * Versatile function/callable library to write state program logic

* RPC and Websocket interfaces to connect
  between other applications or other Automate systems.
* Comprehensive and customizable Web User Interface
* UML graphs can be drawn automaticlaly of the system (as can be seen in the examples of this documentation)

.. _hello-world:

Example
-------

Let's take a look at a small Automate program as an example:

.. code-block:: python

    from automate import *

    class MySystem(System):
        # HW swtich connected Raspberry Pi GPIO port 1
        hardware_switch = RpioSensor(port=1)
        # Switch that is controllable, for example, from WEB interface
        web_switch = UserBoolSensor()
        # Lamp relay that switches lamp on/off, connected to GPIO port 2
        lamp = RpioActuator(port=2)
        # Program that controls the system behaviour
        program = Program(
            active_condition=Or('web_switch', 'hardware_switch'),
            on_activate=SetStatus('lamp', True)
        )


    my_system = MySystem()

This simple example has two sensors ``hardware_switch``, ``web_switch``, actuator (``lamp``) and a ``program`` that
contains logic what to do and when. Here, ``lamp`` is switched on if either ``web_switch`` or ``hardware_switch`` has
status ``True``.

Installing Automate
-------------------

Automate can be installed like ordinary python package. I recommend installation
in within virtual environment (see `virtualenv <https://virtualenv.pypa.io/en/latest/>`_).

#. (optional): Create and start using virtualenv::

    mkvirtualenv automate
    workon automate


#. Install from pypi::

    pip install automate

Optionally, you can specify some of the extras, i.e. web, rpc, raspberrypi, arduino::

   pip install automate[web,rpc,raspberrypi,arduino]

Licence
-------

Automate is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Automate is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Automate.  If not, see http://www.gnu.org/licenses/.

