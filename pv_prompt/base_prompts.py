import asyncio
import json
import logging
from typing import TYPE_CHECKING

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.helpers.api_base import ApiResource

# from prompt_toolkit import prompt
# from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

from prompt_toolkit import prompt

from pv_prompt.print_output import info, print_dict

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pv_prompt.resource_cache import HubCache


class QuitException(Exception):
    pass


class BackException(Exception):
    pass


class InvalidIdException(Exception):
    pass


class Command:
    """Command class. Is bound to a key press."""

    def __init__(self, function_=None, label=None, autoreturn=False):
        self._function = function_ or self._empty
        self.autoreturn = autoreturn
        self._label = label

    def __call__(self, *args, **kwargs):
        return self._function(*args, **kwargs)

    async def _empty(self, *args, **kwargs):
        return None

    @property
    def name(self):
        if self._label:
            return self._label
        else:
            return self._function.__name__

    def __repr__(self):
        return "{}({},{},{}".format(
            self.__class__.__name__,
            self._function.__name__,
            self.name,
            self.autoreturn,
        )


bindings = KeyBindings()


@bindings.add("c-b")
def _(event):
    #LOGGER.debug("raising back exception.")
    raise BackException()


class BasePrompt:
    def __init__(self, commands=None, loop=None):
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self._prompt = "Enter a command: "
        self._commands = {
            "q": Command(function_=self.quit, label="(q)uit"),
            "b": Command(autoreturn=True, label="back"),
        }
        if commands:
            self.register_commands(commands)
        self._auto_return = False

    @property
    def commands(self):
        return self._commands

    def _toolbar_string(self):
        _str = " | ".join(
            (
                "({}) {}".format(key, value.name)
                for key, value in self._commands.items()
            )
        )
        return _str

    def register_commands(self, commands: dict):
        """Adds commands key strokes to watch in that context"""
        self._commands.update(commands)

    async def current_prompt(
        self, prompt_=None, toolbar=None, autocomplete=None, autoreturn=False
    ):
        """The currently active prompt.

        """
        self._auto_return = autoreturn
        if toolbar is not None:
            self._toolbar_string = lambda: toolbar
        if prompt_ is None:
            prompt_ = self._prompt
        try:
            while True:
                # prompt = PromptSession(
                #     prompt_,
                #     bottom_toolbar=self._toolbar_string,
                #     completer=autocomplete,
                # )
                LOGGER.debug(bindings)
                _command = await prompt(
                    async_=True,
                    bottom_toolbar=self._toolbar_string,
                    key_bindings=bindings,
                )
                LOGGER.debug("received command: {}".format(_command))
                _meth = self.commands.get(_command)
                if _meth:
                    LOGGER.debug(
                        "a method tied to this command: {}".format(_meth)
                    )
                    val = await _meth(_command)
                    LOGGER.debug("method return with value: {}".format(val))
                    if _meth.autoreturn:
                        LOGGER.debug("auto returning from the method")
                        return val
                if self._auto_return:
                    LOGGER.debug("Returning with entered command.")
                    return _command
        except BackException:
            return None

    # def back(self, *args, **kwargs):
    #     raise BackException()

    async def quit(self, *args, **kwargs):
        raise QuitException()


class PvPrompt(BasePrompt):
    # def __init__(self, request: AioRequest, commands=None):
    def __init__(
        self, request: AioRequest, hub_cache: "HubCache", commands=None
    ):
        super().__init__(commands=commands)
        self.hub_cache = hub_cache
        self.request = request

        if request:
            self.hub_ip = request.hub_ip
        else:
            self.hub_ip = "not connected"
        self.api_resource = None

    def _toolbar_string(self):
        line1 = super()._toolbar_string()
        return line1 + " \nhub: {}".format(self.hub_ip)


class PvResourcePrompt(PvPrompt):
    def __init__(
        self,
        pv_resource: ApiResource,
        request: AioRequest,
        hub_cache: "HubCache",
    ):
        super().__init__(request, hub_cache)
        self.pv_resource = pv_resource
        self.register_commands(
            {"s": Command(function_=self.show_raw, label="(s)how raw")}
        )

    async def show_raw(self, *args, **kwargs):
        print_dict(self.pv_resource.raw_data)
