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

MESSAGE_CONNECTION_STATE = "connection_state"
MESSAGE_OUTGOING = "out"
MESSAGE_INCOMING = "in"


class NordicConnectionProblem(Exception):
    pass


class NordicWriteProblem(NordicConnectionProblem):
    pass


class NordicReadProblem(NordicConnectionProblem):
    pass


def byte_to_string_rep(byte_instance):
    string_rep = []
    for bt in byte_instance:
        if 32 <= bt < 127:
            string_rep.append(chr(bt))
        else:
            string_rep.append(hex(bt))
    _string_rep = "".join(string_rep)
    return _string_rep


from enum import Enum


class State(Enum):
    disconnected = 0
    idle = 1
    writing = 2


class NordicSerial:
    _read_delay = 0.1

    def __init__(self, loop, serial_port, serial_speed=38400):
        self._network_id = None
        # self.id_change = b"\x00\x03i"
        # self.id_change_response = b"\x03i"
        self.serial = None
        self.port = serial_port
        self.serial_speed = serial_speed
        self.loop = loop
        self.loop.create_task(self.connector())
        self._read_try_count = 10
        self.tries = 0
        self.message_queue = asyncio.Queue()
        self.state = State.idle

    def disconnect(self):
        LOGGER.debug("Disconnecting from serial")
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception as err:
                LOGGER.error(err)
        self.serial = None
        self._set_connection_state(State.disconnected)

    def _set_connection_state(self, state: State):
        self.state = state
        self.message_queue.put_nowait(
            {MESSAGE_CONNECTION_STATE: self.state.name}
        )

    @asyncio.coroutine
    def connector(self):
        """Check connection state in a loop"""
        while True:
            if self.state == State.idle:
                LOGGER.debug("Checking connection")
                if self.serial is not None:
                    LOGGER.debug(self.serial.closed)
                if self.serial is None or self.serial.closed:
                    LOGGER.info("Trying to connect")
                    yield from self.connect()

            yield from asyncio.sleep(5)

    @asyncio.coroutine
    def connect(self):
        """Connects to the serial port and prepares the nordic
        for sending commands to the blinds."""

        yield from self.message_queue.put(
            {MESSAGE_CONNECTION_STATE: self.state.name}
        )

        LOGGER.debug(
            "Connecting to serial port %s. Attempt: %s",
            self.serial_speed,
            self.tries,
        )
        try:
            self.serial = Serial(
                self.port, baudrate=self.serial_speed, timeout=0
            )
        except SerialException:
            yield from self.message_queue.put(
                {MESSAGE_CONNECTION_STATE: self.state.name}
            )

            LOGGER.error("Problem connecting")
            return

        # yield from asyncio.sleep(1)
        # LOGGER.info("Changing dongle id.")
        # self.serial.write(self.id_change)

        LOGGER.info("Connected to serial port %s", self.serial.port)

        self._set_connection_state(State.idle)

    @asyncio.coroutine
    def _write(self, data, response=None):
        _val = None
        try:
            LOGGER.debug("outgoing: %s", data)
            self.serial.write(data)
        except (SerialException, AttributeError) as err:
            LOGGER.error("Problem writing to serial. %s", err)

            raise NordicWriteProblem()
        yield from self.message_queue.put({MESSAGE_OUTGOING: data})

        for i in range(self._read_try_count):
            _val = self.serial.read()
            if _val:
                yield from asyncio.sleep(self._read_delay)
                _val += self.serial.read(self.serial.in_waiting)
                break
            yield from asyncio.sleep(self._read_delay)
        if response:
            if not _val == response:
                LOGGER.error("Dongle response not correct")
                raise NordicReadProblem()
        if _val is None:
            LOGGER.error("Problem reading from serial")
            raise NordicReadProblem()

        yield from self.message_queue.put({MESSAGE_INCOMING: _val})

    @asyncio.coroutine
    def write(self, data):
        self._set_connection_state(State.writing)
        try:
            yield from self._write(data)

        except NordicConnectionProblem:
            self.disconnect()

            self.tries += 1
            LOGGER.info("Write retry %s", self.tries)
            if self.tries < 2:
                yield from asyncio.sleep((self.tries - 1) * 1)
                yield from self.connect()
                yield from self.write(data)
            else:
                LOGGER.debug("unable to send command.")
                self.tries = 0
                self._set_connection_state(State.idle)
        else:
            self._set_connection_state(State.idle)
            LOGGER.debug("changing state to %s", self.state)
            self.tries = 0


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
            "c": Command(function_=self.connect, autoreturn=True),
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
