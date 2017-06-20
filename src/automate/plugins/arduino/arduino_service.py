# -*- coding: utf-8 -*-
# (c) 2015 Tuomas Airaksinen
#
# This file is part of automate-arduino.
#
# automate-arduino is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# automate-arduino is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with automate-arduino.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import os
import threading
import logging
from collections import namedtuple

from builtins import range

from automate import Lock
from traits.api import HasTraits, Any, Dict, CList, Str, Int, List
from automate.service import AbstractSystemService

logger = logging.getLogger('automate.arduino_service')

PinTuple = namedtuple('PinTuple', ['type', 'pin'])

def patch_pyfirmata():
    """ Patch Pin class in pyfirmata to have Traits. Particularly, we need notification
        for value changes in Pins. """

    import pyfirmata
    if getattr(pyfirmata, 'patched', False):
        return

    PinOld = pyfirmata.Pin

    class Pin(PinOld, HasTraits):
        mode = property(PinOld._get_mode, PinOld._set_mode)

        def __init__(self, *args, **kwargs):
            HasTraits.__init__(self)
            self.add_trait("value", Any)
            PinOld.__init__(self, *args, **kwargs)

    import pyfirmata.pyfirmata

    pyfirmata.Pin = Pin
    pyfirmata.pyfirmata.Pin = Pin

    from pyfirmata.util import Iterator as OldIterator

    class FixedPyFirmataIterator(OldIterator):

        def run(iter_self):
            try:
                super(FixedPyFirmataIterator, iter_self).run()
            except Exception as e:
                logger.error('Exception %s occurred in Pyfirmata iterator, quitting now', e)
                logger.error('threads: %s', threading.enumerate())

    pyfirmata.util.Iterator.Fixed = FixedPyFirmataIterator
    pyfirmata.patched = True


class ArduinoService(AbstractSystemService):

    """
        Service that provides interface to Arduino devices via
        `pyFirmata library <https://github.com/tino/pyFirmata>`_.
    """

    #: Arduino devices to use, as a list
    arduino_devs = CList(Str, ["/dev/ttyUSB0"])

    #: Arduino device board types, as a list of strings. Choices are defined by pyFirmata board
    #: class names, i.e. allowed values are "Arduino", "ArduinoMega", "ArduinoDue".
    arduino_dev_types = CList(Str, ["Arduino"])

    #: Arduino device sampling rates, as a list (in milliseconds).
    arduino_dev_sampling = CList(Int, [500])

    _sens_analog = Dict
    _sens_digital = Dict
    _act_digital = Dict
    _boards = List
    _locks = List
    _iterator_thread = Any

    class FileNotReadableError(Exception):
        pass

    def setup(self):
        self.logger.debug("Initializing Arduino subsystem")
        try:
            import pyfirmata
        except ImportError:
            self.logger.error("Please install pyfirmata if you want to use Arduino interface")
            return

        patch_pyfirmata()
        from pyfirmata.util import Iterator, to_two_bytes

        # Initialize configured self.boards
        ard_devs = self.arduino_devs
        ard_types = self.arduino_dev_types
        samplerates = self.arduino_dev_sampling
        assert len(ard_devs) == len(ard_types) == len(samplerates), 'Arduino configuration invalid!'

        for i in range(len(ard_devs)):
            try:
                if not os.access(ard_devs[i], os.R_OK):
                    raise self.FileNotReadableError
                cls = getattr(pyfirmata, ard_types[i])
                board = cls(ard_devs[i])
                board.send_sysex(pyfirmata.SAMPLING_INTERVAL, to_two_bytes(samplerates[i]))
                self._iterator_thread = it = Iterator.Fixed(board)
                it.daemon = True
                it.name = "PyFirmata thread for {dev}".format(dev=ard_devs[i])
                board._iter = it
                it.start()
                self._boards.append(board)
            except (self.FileNotReadableError, OSError) as e:
                if isinstance(e, self.FileNotReadableError) or e.errno == os.errno.ENOENT:
                    self.logger.warning('Your arduino device %s is not available. Arduino will be mocked.', ard_devs[i])
                    self._boards.append(None)
                else:
                    raise e
            self._locks.append(Lock())

    def cleanup(self):
        self.logger.debug("Cleaning up Arduino subsystem. ")
        while self._boards:
            board = self._boards.pop()
            if board:
                board.exit()
        if self._iterator_thread and self._iterator_thread.is_alive():
            self._iterator_thread.board = None
            self._iterator_thread.join()
            self._iterator_thread = None

    def reload(self):
        digital_sensors = list(self._sens_digital.items())
        analog_sensors = list(self._sens_analog.items())
        digital_actuators = list(self._act_digital.items())

        for (dev, pin_nr), (_type, pin) in digital_actuators:
            self.cleanup_digital_actuator(dev, pin_nr)

        for (dev, pin_nr), (sens, pin) in digital_sensors:
            self.unsubscribe_digital(dev, pin_nr)
        for (dev, pin_nr), (sens, pin) in analog_sensors:
            self.unsubscribe_analog(dev, pin_nr)
        super(ArduinoService, self).reload()
        # Restore subscriptions
        for (dev, pin_nr), (sens, pin) in digital_sensors:
            self.subscribe_digital(dev, pin_nr, sens)
        for (dev, pin_nr), (sens, pin) in analog_sensors:
            self.subscribe_analog(dev, pin_nr, sens)

        for (dev, pin_nr), (_type, pin) in digital_actuators:
            setup_func = {'p': self.setup_pwm, 'd': self.setup_digital}.get(_type)
            if setup_func:
                setup_func(dev, pin_nr)
            #TODO: servo reload!

    def setup_digital(self, dev, pin_nr):
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            pin = self._boards[dev].get_pin("d:{pin}:o".format(pin=pin_nr))
            self._act_digital[(dev, pin_nr)] = PinTuple('o', pin)

    def setup_pwm(self, dev, pin_nr):
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            pin = self._boards[dev].get_pin("d:{pin}:p".format(pin=pin_nr))
            self._act_digital[(dev, pin_nr)] = PinTuple('p', pin)

    def setup_servo(self, dev, pin_nr, min_pulse, max_pulse, angle):
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            pin = self._boards[dev].get_pin("d:{pin}:s".format(pin=pin_nr))
            self._act_digital[(dev, pin_nr)] = PinTuple('s', pin)
            self._boards[dev].servo_config(pin_nr, min_pulse, max_pulse, angle)

    def change_digital(self, dev, pin_nr, value):
        """ Change digital Pin value (boolean). Also PWM supported(float)"""
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            self._act_digital[(dev, pin_nr)].pin.write(value)

    # Functions for input signals
    def handle_analog(self, obj, name, old, new):
        dev = obj.__dev_id
        pin = obj.pin_number
        if not self._boards[dev]:
            return
        self._sens_analog[(dev, pin)][0].set_status(new)

    def handle_digital(self, obj, name, old, new):
        dev = obj.__dev_id
        pin = obj.pin_number
        if not self._boards[dev]:
            return
        self._sens_digital[(dev, pin)][0].set_status(new)

    def subscribe_analog(self, dev, pin_nr, sens):
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            pin = self._boards[dev].get_pin("a:{pin}:i".format(pin=pin_nr))
            pin.__dev_id = dev
            self._sens_analog[(dev, pin_nr)] = (sens, pin)
            s = pin.read()
        if s is not None:
            sens.set_status(s)
        pin.on_trait_change(self.handle_analog, "value")

    def cleanup_digital_actuator(self, dev, pin_nr):
        pin = self._act_digital.pop((dev, pin_nr), None)

    def unsubscribe_digital(self, dev, pin_nr):
        pin = self._sens_digital.pop((dev, pin_nr), None)
        if pin:
            pin[1].remove_trait('value')

    def unsubscribe_analog(self, dev, pin_nr):
        pin = self._sens_analog.pop((dev, pin_nr), None)
        if pin:
            pin[1].remove_trait('value')

    def subscribe_digital(self, dev, pin_nr, sens):
        if not self._boards[dev]:
            return
        with self._locks[dev]:
            pin = self._boards[dev].get_pin("d:{pin}:i".format(pin=pin_nr))
            pin.__dev_id = dev
            self._sens_digital[(dev, pin_nr)] = (sens, pin)
            s = pin.read()
        if s is not None:
            sens.set_status(s)
        pin.on_trait_change(self.handle_digital, "value")
