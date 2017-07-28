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
from collections import namedtuple, defaultdict

import pyfirmata
import pyfirmata.pyfirmata
import pyfirmata.util
import time
from traits.api import HasTraits, Any, Str, Int, CInt, CBool

from automate import Lock
from automate.service import AbstractSystemService
from automate.common import threaded

logger = logging.getLogger(__name__)

PinTuple = namedtuple('PinTuple', ['type', 'pin'])

# Pin modes
PIN_MODE_PULLUP = 0x0B

# Sysex to arduino
SYSEX_VIRTUALWIRE_MESSAGE = 0x00
SYSEX_KEEP_ALIVE = 0x01
SYSEX_SETUP_VIRTUALWIRE = 0x02

VIRTUALWIRE_SET_PIN_MODE = 0x01
VIRTUALWIRE_ANALOG_MESSAGE = 0x02
VIRTUALWIRE_DIGITAL_MESSAGE = 0x03
VIRTUALWIRE_START_SYSEX = 0x04
VIRTUALWIRE_SET_DIGITAL_PIN_VALUE = 0x05
VIRTUALWIRE_DIGITAL_BROADCAST = 0x06
VIRTUALWIRE_ANALOG_BROADCAST = 0x07


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
    # Make necessary fixes to pyfirmata library

    if getattr(pyfirmata, 'patched', False):
        return

    # Patch Pin class in pyfirmata to have Traits. Particularly, we need notification
    # for value changes in Pins. """

    PinOld = pyfirmata.Pin

    class Pin(PinOld, HasTraits):
        mode = property(PinOld._get_mode, PinOld._set_mode)

        def __init__(self, *args, **kwargs):
            HasTraits.__init__(self)
            self.add_trait("value", Any)
            PinOld.__init__(self, *args, **kwargs)

    pyfirmata.Pin = Pin
    pyfirmata.pyfirmata.Pin = Pin

    # Fix bug in Board class (global dictionary & list) # TODO fix upstream...

    OldBoard = pyfirmata.Board
    class FixedBoard(OldBoard):
        def __init__(self, *args, **kwargs):
            self._command_handlers = {}
            self._stored_data = []
            super(FixedBoard, self).__init__(*args, **kwargs)

    pyfirmata.Board = FixedBoard
    pyfirmata.pyfirmata.Board = FixedBoard
    pyfirmata.BOARD_SETUP_WAIT_TIME = 0
    pyfirmata.pyfirmata.BOARD_SETUP_WAIT_TIME = 0
    pyfirmata.patched = True

patch_pyfirmata()


def iterate_serial(board):
    while True:
        while board.bytes_available():
            try:
                board.iterate()
            except Exception as e:
                logger.exception('Exception in board.iterate: %s', e)
        time.sleep(0.01)


class ArduinoService(AbstractSystemService):

    """
        Service that provides interface to Arduino devices via
        `pyFirmata library <https://github.com/tino/pyFirmata>`_.
    """

    #: Arduino devices to use, as a list
    device = Str("/dev/ttyUSB0")

    #: Arduino device board type, choices: 'arduino', 'arduino_mega', 'arduino_due'.
    device_type = Str('arduino')

    #: Arduino sample rate in milliseconds (i.e. how often to send data to host)
    sample_rate = Int(500)

    #: Device home address (0-255) in VirtualWire network. This should be same for all
    #: devices in a network.
    home_address = CInt(0)

    #: Device address (0-255) in VirtualWire network. Unique for each device.
    device_address = CInt(0)

    #: VirtualWire transfer pin
    virtualwire_tx_pin = CInt(0)

    #: VirtualWire receiver pin
    virtualwire_rx_pin = CInt(0)

    #: VirtualWire PTT (push to talk) pin
    virtualwire_ptt_pin = CInt(0)

    #: Wakeup pin (0 to disable) that wakes Arduino from sleep mode. On Atmega328 based boards,
    #: possible values are 2 and 3
    wakeup_pin = CInt(0)

    #: VirtualWire speed, (bit rate = speed * 1000 bps). Values 1-9 are allowed.
    #: Values up to 7 should be working, but your mileage may vary.
    virtualwire_speed = CInt(2)

    #: Send keep-alive messages periodically over serial port to prevent Arduino device from
    #: falling to power save mode.
    keep_alive = CBool(True)

    def __init__(self, *args, **kwargs):
        super(ArduinoService, self).__init__(*args, **kwargs)

        self._sens_analog = {}
        self._sens_digital = {}
        self._sens_virtualwire_digital = defaultdict(list) # source device -> list of sensors
        self._sens_virtualwire_analog = defaultdict(list) # source device -> list of sensors
        self._act_digital = {}
        self._board = None
        self._lock = None
        self._iterator_thread = None

    class FileNotReadableError(Exception):
        pass

    def setup(self):
        self.logger.debug("Initializing Arduino subsystem")

        # Initialize configured self.boards

        try:
            if not os.access(self.device, os.R_OK):
                raise self.FileNotReadableError
            board = pyfirmata.Board(self.device, layout=pyfirmata.BOARDS[self.device_type])
            self._board = board
            self.is_mocked = False
        except (self.FileNotReadableError, OSError) as e:
            if isinstance(e, self.FileNotReadableError) or e.errno == os.errno.ENOENT:
                self.logger.warning('Your arduino device %s is not available. Arduino will be mocked.',
                                    self.device)
                self._board = None
                self.is_mocked = True
            else:
                raise
        self._lock = Lock()
        if self._board:
            self._board.add_cmd_handler(pyfirmata.STRING_DATA, self._string_data_handler)
            self._iterator_thread = it = threading.Thread(target=threaded(self.system, iterate_serial,
                                                                          self._board))
            it.daemon = True
            it.name = "PyFirmata thread for {dev}".format(dev=self.device)
            it.start()

            self.write(pyfirmata.SYSTEM_RESET)
            self._board.send_sysex(pyfirmata.SAMPLING_INTERVAL,
                                   pyfirmata.util.to_two_bytes(self.sample_rate))

            self.configure_virtualwire()
            self._keep_alive()

    def configure_virtualwire(self):
        if not self._board:
            return
        with self._lock:
            self.logger.debug('Configuring wirtualwire')
            self._board.send_sysex(SYSEX_SETUP_VIRTUALWIRE, [self.virtualwire_rx_pin,
                                                             self.virtualwire_tx_pin,
                                                             self.virtualwire_ptt_pin,
                                                             self.wakeup_pin,
                                                             self.virtualwire_speed,
                                                             self.home_address,
                                                             self.device_address,
                                                             ])
            self.setup_virtualwire_input()

    def _keep_alive(self):
        if self.keep_alive:
            self.logger.debug('Sending keep-alive message to Arduino')
            self._board.send_sysex(SYSEX_KEEP_ALIVE, [0])
        interval = 60
        self._keepalive_thread = threading.Timer(interval, threaded(self.system, self._keep_alive))
        self._keepalive_thread.name = "Arduino keepalive (60s)"
        self._keepalive_thread.start()


    def _string_data_handler(self, *data):
        self.logger.debug('String data: %s', bytearray(data[::2]).decode('ascii'))

    def cleanup(self):
        self.logger.debug("Cleaning up Arduino subsystem. ")
        if self._board:
             self._board.exit()
        if self._iterator_thread and self._iterator_thread.is_alive():
            self._iterator_thread.join()
        if self._keepalive_thread:
            self._keepalive_thread.cancel()

    def reload(self):
        digital_sensors = list(self._sens_digital.items())
        analog_sensors = list(self._sens_analog.items())
        digital_actuators = list(self._act_digital.items())
        #virt_analog = list(self._sens_virtualwire_analog.items())
        #virt_digital = list(self._sens_virtualwire_digital.items())

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

    def send_virtualwire_command(self, recipient, command, *args):
        if not self._board:
            return
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
            board.send_sysex(SYSEX_VIRTUALWIRE_MESSAGE, data)

    def setup_virtualwire_input(self):
        if not self._board:
            return
        self._board.add_cmd_handler(SYSEX_VIRTUALWIRE_MESSAGE, self._virtualwire_message_callback)

    def _virtualwire_message_callback(self, sender_address, command, *data):
        self.logger.debug('pulse %s %s %s', int(sender_address), hex(command), bytearray(data))
        if command == VIRTUALWIRE_DIGITAL_BROADCAST:
            if len(data) != 2:
                self.logger.error('Broken digital data: %s %s %s', sender_address, command, data)
                return
            port_nr, value = data
            for s in self._sens_virtualwire_digital[sender_address]:
                port = s.pin // 8
                pin_in_port = s.pin % 8
                if port_nr == port:
                    s.status = bool(value & 1 << pin_in_port)
        elif command == VIRTUALWIRE_ANALOG_BROADCAST:
            if len(data) != 3:
                self.logger.error('Broken analog data: %s %s %s', sender_address, command, data)
                return
            pin, msb, lsb = data
            value = (msb << 8) + lsb
            value = value/1023.  # Arduino gives 10 bit resolution
            self.logger.debug('Analog data: %s %s', pin, value)
            for s in self._sens_virtualwire_analog[sender_address]:
                if s.pin == pin:
                    s.status = value

    def write(self, *data):
        data = bytearray(data)
        if not self._board:
            return
        with self._lock:
            self.logger.debug('Writing %s', data)
            self._board.sp.write(data)

    def subscribe_virtualwire_digital_broadcast(self, sensor, source_device):
        self._sens_virtualwire_digital[source_device].append(sensor)

    def unsubscribe_virtualwire_digital_broadcast(self, sensor, source_device):
        self._sens_virtualwire_digital[source_device].remove(sensor)

    def subscribe_virtualwire_analog_broadcast(self, sensor, source_device):
        self._sens_virtualwire_analog[source_device].append(sensor)

    def unsubscribe_virtualwire_analog_broadcast(self, sensor, source_device):
        self._sens_virtualwire_analog[source_device].remove(sensor)

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
        if not self._board:
            return
        self.logger.debug('Setting pin mode for pin %s to %s', pin_number, mode)
        self.write(pyfirmata.SET_PIN_MODE, pin_number, mode)
