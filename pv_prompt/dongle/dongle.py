"""All serial handling with the nordic dongle."""

import asyncio
import logging
from enum import Enum

from prompt_toolkit.completion import WordCompleter
from serial import Serial
from serial.serialutil import SerialException
from serial.tools.list_ports import comports

from pv_prompt.base_prompts import BasePrompt, Command
from pv_prompt.print_output import info

LOGGER = logging.getLogger(__name__)


def byte_to_string_rep(byte_instance):
    string_rep = []
    for bt in byte_instance:
        if 32 <= bt < 127:
            string_rep.append(chr(bt))
        else:
            string_rep.append(hex(bt))
    _string_rep = "".join(string_rep)
    return _string_rep


def get_id(powerview_id=17520):
    return _from_int(powerview_id)


def _from_int(network_id):
    return network_id.to_bytes(2, byteorder="big")


class State(Enum):
    connected = 1  # connected and ready for sending out data
    need_reset = 2
    connecting = 3
    disconnected = 4
    waiting_for_response = 5  # connected. Waiting for incoming data


class NordicSerial:
    """Serial connection manager"""

    def __init__(self, loop, serial_port, serial_speed=38400):
        self.network_id = byte_to_string_rep(get_id())

        self.id_change = b"\x00\x03i" + get_id()
        self.id_change_response = b"\x03i" + get_id()

        self.s = None
        self.port = serial_port
        self.serial_speed = serial_speed

        self.connect_attempts = 1
        self.loop = loop  # The main event loop.
        self.loop.create_task(self.connect())

        self._read_try_count = 10
        self._read_loop = 0.2
        self._waiting_for_input = False

        self.state = State.disconnected

    @asyncio.coroutine
    def connect(self):
        """Continuously trying to connect to the serial port in a loop."""
        LOGGER.info("Starting connection loop.")

        while True:
            if self.state == State.connected:
                yield from self._watch()
            if self.state == State.need_reset:
                yield from self._reset()
            if self.state == State.disconnected:
                yield from self._connect()
            if self.state == State.connecting:
                pass
            if self.state == State.waiting_for_response:
                pass

            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def _reset(self):
        LOGGER.info("Resetting serial.")
        self.state = State.disconnected
        # self._waiting_for_input = False

        if self.s:
            try:
                self.s.close()
            except (Exception) as err:
                LOGGER.error("Closing error: %s", err)
        # self.state = State.disconnected
        # yield from asyncio.sleep(2)

    @asyncio.coroutine
    def _connect(self):
        """Connects to the serial port and prepares the nordic
        for sending commands to the blinds."""
        try:
            self.state = State.connecting
            LOGGER.debug(
                "Connecting to serial port %s. Attempt: %s",
                self.serial_speed,
                self.connect_attempts,
            )
            if self.s is None:
                self.s = Serial(
                    self.port, baudrate=self.serial_speed, timeout=0
                )
            else:
                self.s.open()

            yield from asyncio.sleep(1)

            yield from self.send_dongle_id()
            if self.state == State.need_reset:
                return

            self.connect_attempts = 1
            self.state = State.connected
            LOGGER.info("Connected to serial port {}".format(self.s.port))
        except (SerialException, FileNotFoundError, Exception) as err:
            self.state = State.need_reset
            LOGGER.error("Problem connecting. %s", err)
            self.connect_attempts += 1

    @asyncio.coroutine
    def send_dongle_id(self):
        """Set ID of dongle."""
        _val = yield from self._write(self.id_change)
        LOGGER.debug("Incoming on connect: %s", _val)

        if _val and self.id_change_response in _val:
            return _val
        else:
            self.state = State.need_reset
            return None

    @asyncio.coroutine
    def _watch(self):
        try:
            if not self._waiting_for_input:
                self.s.read()
        except Exception as err:
            LOGGER.error("Watchdog failed: %s", err)
            self.state = State.need_reset

    @asyncio.coroutine
    def _write(self, data):
        _val = None
        tries = self._read_try_count
        LOGGER.debug("Try count: %s", tries)
        self._waiting_for_input = True

        try:
            self.s.write(data)
        except Exception as err:
            LOGGER.error("Problem writing to serial. %s", err)
            self.state = State.need_reset
            return False

        yield from asyncio.sleep(0.1)
        while True:
            if tries > self._read_try_count:
                break

            _val = self.s.read()
            if _val:
                yield from asyncio.sleep(self._read_loop)
                _val += self.s.read(self.s.in_waiting)
                break

            yield from asyncio.sleep(self._read_loop)
            tries += 1

        yield from asyncio.sleep(0.4)
        self._waiting_for_input = False
        return _val

    @asyncio.coroutine
    def write_to_nordic(self, data):
        """Write data to the nordic dongle."""
        LOGGER.debug("Writing data to dongle: %s", data)
        if self.state == State.connected:
            response = yield from self._write(data)
            LOGGER.debug("Serial response: %s", response)
            return response


class Connect(BasePrompt):
    ATTR_VID = "vid"
    ATTR_PID = "pid"
    ATTR_NAME = "name"

    dongles = [
        {ATTR_VID: 1027, ATTR_PID: 24597, ATTR_NAME: "Bremerhaven dongle"},
        {ATTR_VID: 4966, ATTR_PID: 4117, ATTR_NAME: "Nordic dongle"},
    ]

    def __init__(self):
        commands = {
            "s": Command(function_=self.search_port),
            "c": Command(function_=self.connect, autoreturn=True)
        }
        super().__init__(commands=commands)
        self.port_suggestions = []
        self.port = None

    async def search_port(self, *args, **kwargs):
        for i in comports():
            for _dongle in self.dongles:
                if (
                        i.pid == _dongle[self.ATTR_PID]
                        and i.vid == _dongle[self.ATTR_VID]
                ):
                    info(
                        "Serial port found. vid: {} pid: {} name: {}".format(
                            i.pid, i.vid, i.device
                        )
                    )
                    self.port_suggestions.append(i.device)

    async def connect(self, *args, **kwargs):
        base_prompt = BasePrompt()
        port = await base_prompt.current_prompt(
            "Enter serial port: ",
            autoreturn=True,
            autocomplete=WordCompleter(self.port_suggestions),
        )

        return port
