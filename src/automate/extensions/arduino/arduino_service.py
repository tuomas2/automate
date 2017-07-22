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
import struct
import threading
import logging
from collections import namedtuple
import pyfirmata

from automate import Lock
from traits.api import HasTraits, Any, Dict, CList, Str, Int, List, CInt, CStr
from automate.service import AbstractSystemService

logger = logging.getLogger(__name__)

PinTuple = namedtuple('PinTuple', ['type', 'pin'])

PIN_MODE_VIRTUALWIRE_WRITE = 0x0C
PIN_MODE_VIRTUALWIRE_READ = 0x0D
SYSEX_VIRTUALWRITE_MESSAGE = 0x80

# Custom message command bytes (Firmata commands)
CUSTOM_MESSAGE = 0xF1
SET_VIRTUAL_PIN_VALUE = 0xF2
SET_DIGITAL_PIN_VALUE = 0xF5

# Pin modes
PIN_MODE_PULLUP = 0x0B

# Our custom command codes, from arduino to here.
#CMD_CUSTOM_MESSAGE = 0x01
#CMD_VIRTUAL_PIN = 0x02

TYPE_INT = 0x01
TYPE_FLOAT = 0x02
TYPE_STR = 0x03


def float_to_bytes(value):
    return bytearray(struct.pack('!f', value))


def bytes_to_float(value):
    return struct.unpack('!f', value)[0]


def float_to_twobytes(value):
    value = int(round(value * 255))
    val = bytearray([value % 128, value >> 7])
    return val


def twobytes_to_float(lsb, msb):
    return round(float((msb << 7) + lsb) / 1023, 4)


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
                logger.exception('Exception %s occurred in Pyfirmata iterator, quitting now. '
                                 'Threads: ', e, threading.enumerate())

    pyfirmata.util.Iterator.Fixed = FixedPyFirmataIterator
    pyfirmata.patched = True


class ArduinoService(AbstractSystemService):

    """
        Service that provides interface to Arduino devices via
        `pyFirmata library <https://github.com/tino/pyFirmata>`_.
    """

    #: Arduino devices to use, as a list
    device = Str("/dev/ttyUSB0")

    #: Arduino device board types, as a list of strings. Choices are defined by pyFirmata board
    #: class names, i.e. allowed values are "Arduino", "ArduinoMega", "ArduinoDue".
    device_type = Str('Arduino')

    #: Arduino device sampling rates, as a list (in milliseconds).
    sample_rate = Int(500)

    #: VirtualWire communication protocol home address
    home_address = CInt(0)

    #: VirtualWire communication protocol device address
    device_address = CInt(0)

    #: VirtualWire transfer pin
    virtualwire_tx_pin = CInt(0)

    #: VirtualWire receiver pin
    virtualwire_rx_pin = CInt(0)

    _sens_analog = Dict
    _sens_digital = Dict
    _sens_virtual = Dict
    _sens_virtual_message_sensors = List

    _act_digital = Dict
    _board = Any
    _lock = Any
    _iterator_thread = Any

    class FileNotReadableError(Exception):
        pass

    def setup(self):
        self.logger.debug("Initializing Arduino subsystem")

        patch_pyfirmata()
        from pyfirmata.util import Iterator, to_two_bytes

        # Initialize configured self.boards

        try:
            if not os.access(self.device, os.R_OK):
                raise self.FileNotReadableError
            cls = getattr(pyfirmata, self.device_type)
            board = cls(self.device)
            board.send_sysex(pyfirmata.SAMPLING_INTERVAL, to_two_bytes(self.sample_rate))
            self._iterator_thread = it = Iterator.Fixed(board)
            it.daemon = True
            it.name = "PyFirmata thread for {dev}".format(dev=self.device)
            board._iter = it
            it.start()
            self._board = board
            self.is_mocked = False
        except (self.FileNotReadableError, OSError) as e:
            if isinstance(e, self.FileNotReadableError) or e.errno == os.errno.ENOENT:
                self.logger.warning('Your arduino device %s is not available. Arduino will be mocked.', self.device)
                self._board = None
                self.is_mocked = True
            else:
                raise
        self._lock = Lock()

        if self.virtualwire_tx_pin:
            self.setup_virtualwire_output()
        if self.virtualwire_rx_pin:
            self.setup_virtualwire_input()


    def cleanup(self):
        self.logger.debug("Cleaning up Arduino subsystem. ")
        if self._board:
             self._board.exit()
        if self._iterator_thread and self._iterator_thread.is_alive():
            self._iterator_thread.board = None
            self._iterator_thread.join()
            self._iterator_thread = None

    def reload(self):
        digital_sensors = list(self._sens_digital.items())
        analog_sensors = list(self._sens_analog.items())
        digital_actuators = list(self._act_digital.items())

        for pin_nr, (_type, pin) in digital_actuators:
            self.cleanup_digital_actuator(pin_nr)

        for pin_nr, (sens, pin) in digital_sensors:
            self.unsubscribe_digital(pin_nr)
        for pin_nr, (sens, pin) in analog_sensors:
            self.unsubscribe_analog(pin_nr)
        super(ArduinoService, self).reload()
        # Restore subscriptions
        for pin_nr, (sens, pin) in digital_sensors:
            self.subscribe_digital(pin_nr, sens)
        for pin_nr, (sens, pin) in analog_sensors:
            self.subscribe_analog(pin_nr, sens)

        for pin_nr, (_type, pin) in digital_actuators:
            setup_func = {'p': self.setup_pwm, 'o': self.setup_digital}.get(_type)
            # TODO: servo reload not implemented
            if setup_func:
                setup_func(pin_nr)
            else:
                self.logger.error('Reloading not implemented for type %s (pin %d)', _type, pin_nr)
        self.logger.info('Arduino pins are now set up!')

    def send_virtualwire_message(self, recipient, message):
        if not self._board:
            return
        with self._lock:
            board = self._board
            data = (bytearray([self.home_address, self.device_address, recipient, CUSTOM_MESSAGE]) +
                    bytearray(message.encode('utf-8')))
            self.logger.debug('VW: Sending message %s', data)
            board.send_sysex(SYSEX_VIRTUALWRITE_MESSAGE, data)

    def send_virtualwire_command(self, recipient, command, *args):
        with self._lock:
            board = self._board
            data = bytearray([self.home_address, self.device_address, recipient, command])
            for a in args:
                if isinstance(a, bytearray):
                    data.extend(a)
                elif isinstance(a, str):
                    data.extend(bytearray(a.encode('utf-8')))
                else:
                    data.append(a)
            self.logger.debug('VW: Sending command %s', data)
            board.send_sysex(SYSEX_VIRTUALWRITE_MESSAGE, data)

    def setup_virtualwire_output(self):
        if not self._board:
            return
        with self._lock:
            board = self._board
            board.sp.write(bytearray([pyfirmata.SET_PIN_MODE, self.virtualwire_tx_pin, PIN_MODE_VIRTUALWIRE_WRITE]))

    def setup_virtualwire_input(self):
        if not self._board:
            return
        with self._lock:
            board = self._board
            board.sp.write(bytearray([pyfirmata.SET_PIN_MODE, self.virtualwire_rx_pin, PIN_MODE_VIRTUALWIRE_READ]))
            self._board.add_cmd_handler(pyfirmata.DIGITAL_PULSE, self._virtualwire_message_callback)

    def subscribe_virtualwire_virtual_pin(self, sens, virtual_pin):
        self._sens_virtual[virtual_pin] = sens

    def unsubscribe_virtualwire_virtual_pin(self, virtual_pin):
        self._sens_virtual.pop(virtual_pin)

    def _virtualwire_message_callback(self, command, *data):
        from pyfirmata.util import from_two_bytes
        self.logger.debug('pulse %s %s', data, bytearray(data))
        if command == CUSTOM_MESSAGE:
            self.logger.debug('Custom message')
            for sensor in self._sens_virtual_message_sensors:
                sensor.status = bytes(bytearray(data)).decode('utf-8')
        elif command == SET_VIRTUAL_PIN_VALUE:
            pin_nr = int(data[0])
            type_id = int(data[1])
            converted_data = None
            if type_id == TYPE_INT:
               converted_data = int(data[2])
            elif type_id == TYPE_FLOAT:
               converted_data = bytes_to_float(bytearray(data[2:]))
            elif type_id == TYPE_STR:
               converted_data = bytes(bytearray(data[2:])).decode('utf-8')

            self.logger.debug('Virtual pin value %s %s %s', pin_nr, type_id, converted_data)
            self._sens_virtual[pin_nr].status = converted_data

    def subscribe_virtualwire_messages(self, sens):
        self._sens_virtual_message_sensors.append(sens)

    def unsubscribe_virtual_messages(self, sens):
        self._sens_virtual_message_sensors.remove(sens)


    def setup_digital(self, pin_nr):
        if not self._board:
            self._act_digital[pin_nr] = PinTuple('o', None)
            return
        with self._lock:
            pin = self._board.get_pin("d:{pin}:o".format(pin=pin_nr))
            self._act_digital[pin_nr] = PinTuple('o', pin)

    def setup_pwm(self, pin_nr):
        if not self._board:
            self._act_digital[pin_nr] = PinTuple('p', None)
            return
        with self._lock:
            pin = self._board.get_pin("d:{pin}:p".format(pin=pin_nr))
            self._act_digital[pin_nr] = PinTuple('p', pin)

    def setup_servo(self, pin_nr, min_pulse, max_pulse, angle):
        if not self._board:
            self._act_digital[pin_nr] = PinTuple('s', None)
            return
        with self._lock:
            pin = self._board.get_pin("d:{pin}:s".format(pin=pin_nr))
            self._act_digital[pin_nr] = PinTuple('s', pin)
            self._board.servo_config(pin_nr, min_pulse, max_pulse, angle)

    def change_digital(self, pin_nr, value):
        """ Change digital Pin value (boolean). Also PWM supported(float)"""
        if not self._board:
            return
        with self._lock:
            self._act_digital[pin_nr].pin.write(value)

    # Functions for input signals
    def handle_analog(self, obj, name, old, new):
        pin = obj.pin_number
        if not self._board:
            return
        self._sens_analog[pin][0].set_status(new)

    def handle_digital(self, obj, name, old, new):
        pin = obj.pin_number
        if not self._board:
            return
        self._sens_digital[pin][0].set_status(new)

    def subscribe_analog(self, pin_nr, sens):
        if not self._board:
            return
        with self._lock:
            pin = self._board.get_pin("a:{pin}:i".format(pin=pin_nr))
            self._sens_analog[pin_nr] = (sens, pin)
            s = pin.read()
        if s is not None:
            sens.set_status(s)
        pin.on_trait_change(self.handle_analog, "value")

    def cleanup_digital_actuator(self, pin_nr):
        pin = self._act_digital.pop(pin_nr, None)

    def cleanup_virtualwire_actuator(self, pin_nr):
        pin = self._act_digital.pop(pin_nr, None)

    def unsubscribe_digital(self, pin_nr):
        pin = self._sens_digital.pop(pin_nr, None)
        if pin:
            pin[1].remove_trait('value')

    def unsubscribe_analog(self, pin_nr):
        pin = self._sens_analog.pop(pin_nr, None)
        if pin:
            pin[1].remove_trait('value')

    def subscribe_digital(self, pin_nr, sens):
        if not self._board:
            return
        with self._lock:
            pin = self._board.get_pin("d:{pin}:i".format(pin=pin_nr))
            self._sens_digital[pin_nr] = (sens, pin)
            s = pin.read()
        if s is not None:
            sens.set_status(s)
        pin.on_trait_change(self.handle_digital, "value")

    def set_pin_mode(self, pin_number, mode):
        self._board.sp.write(bytearray([pyfirmata.SET_PIN_MODE, self.pin_number, mode]))

