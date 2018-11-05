import logging

from aiopvapi.helpers.constants import (
    ATTR_POSITION,
    ATTR_POSKIND1,
    ATTR_POSITION1,
    ATTR_POSKIND2,
    ATTR_POSITION2,
)
from aiopvapi.resources.shade import BaseShade, ShadeBottomUpTiltAnywhere, MAX_POSITION
from prompt_toolkit.completion import WordCompleter

from pv_prompt.base_prompts import (
    PvResourcePrompt,
    Command,
    PvPrompt,
    InvalidIdException,
    ListPrompt,
    NumberPrompt,
)
from pv_prompt.print_output import (
    info,
    print_shade_data,
    warn,
    print_key_values,
    print_waiting_done,
)
from pv_prompt.resource_cache import HubCache

LOGGER = logging.getLogger(__name__)


class Shade(PvResourcePrompt):
    def __init__(self, shade: BaseShade, request, hub_cache):
        super().__init__(shade, request, hub_cache)
        self._prompt = "shade {} {}: ".format(shade.id, shade.name)
        self.position = None
        self.register_commands(
            {
                "j": Command(function_=self.jog, label="(j)og"),
                "r": Command(function_=self.refresh),
                "s": Command(function_=self.stop),
                "m": Command(function_=self.move),
            }
        )
        if shade.can_move:
            self.register_commands(
                {"o": Command(function_=self.open), "c": Command(function_=self.close)}
            )
        if shade.can_tilt:
            self.register_commands(
                {
                    "u": Command(function_=self.tilt_open),
                    "d": Command(function_=self.tilt_close),
                }
            )

    async def move(self, *args, **kwargs):
        position = Position(self.pv_resource, self.request, self.hub_cache)
        self.position = await position.current_prompt("define a position.")

    async def refresh(self, *args, **kwargs):
        await self.pv_resource.refresh()

    async def jog(self, *args, **kwargs):
        await self.pv_resource.jog()

    async def open(self, *args, **kwargs):
        done = print_waiting_done("Opening")
        await self.pv_resource.open()
        await done()

    async def close(self, *args, **kwargs):
        done = print_waiting_done("Closing")
        await self.pv_resource.close()
        await done()

    async def tilt_close(self, *args, **kwargs):
        await self.pv_resource.tilt_close()

    async def tilt_open(self, *args, **kwargs):
        await self.pv_resource.tilt_open()

    async def stop(self, *args, **kwargs):
        await self.pv_resource.stop()


class Shades(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        # self._shades_resource = PvShades(request)
        self.api_resource = hub_cache.shades
        self.register_commands(
            {
                "l": Command(function_=self._list_shades),
                "s": Command(function_=self._select_shade),
            }
        )
        self._prompt = "Shades: "

    async def _list_shades(self, *args, **kwargs):
        await self.hub_cache.shades.get_resource()
        info("")  # print a newline
        print_shade_data(self.hub_cache.shades)

    async def _select_shade(self, *args, **kwargs):
        try:
            pv_shade = await self.hub_cache.shades.select_resource()
            shade = Shade(pv_shade, self.request, self.hub_cache)
            await shade.current_prompt()
        except InvalidIdException as err:
            warn(err)


class Position(PvPrompt):
    """Define a position object for the shade to move too."""

    def __init__(self, shade: BaseShade, request, hub_cache):
        super().__init__(request, hub_cache)
        self._shade = shade
        self._position = None
        self.register_commands(
            {
                "l": Command(
                    function_=self._list_positions, label="Select allowed position"
                ),
                "m": Command(function_=self.move),
            }
        )
        self._number_completer = WordCompleter([str(MAX_POSITION)])

    async def current_prompt(
        self,
        prompt_=None,
        toolbar=None,
        autocomplete=None,
        autoreturn=False,
        default="",
    ):
        if len(self._shade.allowed_positions) == 1:
            self._position = self._shade.allowed_positions[0]
        else:
            await self._list_positions()

        self._print_position(self._position)

        await self.move()

        await super().current_prompt()

    def _print_position(self, position):
        print_key_values("Position format: ", position)

    async def _list_positions(self, *args, **kwargs):
        positions = ListPrompt(self._shade.allowed_positions)
        self._position = await positions.current_prompt("Select an allowed position")
        self._print_position(self._position)

    async def put_values(self, *args, **kwargs):
        number = NumberPrompt()
        positions = self._position[ATTR_POSITION]
        if ATTR_POSKIND1 in positions:
            positions[ATTR_POSITION1] = await number.current_prompt(
                "Enter a position1: ",
                autoreturn=True,
                autocomplete=self._number_completer,
            )
        if ATTR_POSKIND2 in positions:
            positions[ATTR_POSITION2] = await number.current_prompt(
                "Enter a position2: ",
                autoreturn=True,
                autocomplete=self._number_completer,
            )

    async def move(self, *args, **kwargs):
        await self.put_values()
        print_key_values("moving to:", self._position[ATTR_POSITION])
        await self._shade.move(self._position[ATTR_POSITION])
