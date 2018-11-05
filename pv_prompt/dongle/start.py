import asyncio
import logging
from argparse import ArgumentParser

from prompt_toolkit.eventloop import use_asyncio_event_loop

from pv_prompt.base_prompts import (
    BasePrompt,
    Command,
    YesNoPrompt,
    QuitException,
)
from pv_prompt.dongle.dongle import State, Connect, NordicSerial
from pv_prompt.dongle.nordic import Nd
from pv_prompt.helpers import set_verbosity
from pv_prompt.print_output import (
    info,
    warn,
    print_waiting_done,
    print_key_values,
)

LOGGER = logging.getLogger(__name__)


def activate_scene(scene_id):
    activate = b"\x00\x03SG" + bytes((scene_id,))
    return activate


class MainMenu(BasePrompt):
    def __init__(self, loop, port=None, verbose=False):
        self.loop = loop
        super().__init__()

        self._prompt = "Dongle toolkit: "

        self._register_commands()
        self._port = port
        self.s = None

        # self.s = NordicSerial(loop, port)

    def _register_commands(self):
        self.register_commands(
            {
                "c": Command(function_=self._connect_shade, label="(c)onnect"),
                "j": Command(function_=self._jog, label="(j)og"),
                "e": Command(
                    function_=self._query_scenes, label="qu(e)ry scenes"
                ),
            }
        )

    async def _connect_dongle(self):
        if not self._port:
            _port = await Connect().current_prompt()
            if _port:
                self._port = _port
        self.s = NordicSerial(self.loop, self._port)
        print_key_values("network id", self.s.network_id)
        done = print_waiting_done("Connecting to dongle")
        while not self.s.state == State.connected:
            await asyncio.sleep(0.5)
        await done()

    async def current_prompt(
        self,
        prompt_=None,
        toolbar=None,
        autocomplete=None,
        autoreturn=False,
        default="",
    ):
        await self._connect_dongle()

        await super().current_prompt(
            prompt_, toolbar, autocomplete, autoreturn
        )

    async def _query_scenes(self, *args, **kwargs):
        done = print_waiting_done("Moving to open position")
        await self.s.write_to_nordic(Nd.open.value)
        await asyncio.sleep(3)
        await done()
        for scene_idx in range(0, 32):
            if not self.s.state == State.connected:
                await self._connect_dongle()
            info("Activating scene {}".format(scene_idx))
            await self.s.write_to_nordic(activate_scene(scene_idx))
            done = print_waiting_done("Watch for response")
            await asyncio.sleep(2)
            await done()

    async def _jog(self, *args, **kwargs):
        done = print_waiting_done("Jogging")
        await self.s.write_to_nordic(Nd.JOG.value)
        await done()

    async def _connect_shade(self, *args, **kwargs):
        print("Press shade button")
        await asyncio.sleep(3)
        await self.s.write_to_nordic(Nd.NETWORKADD.value)
        await asyncio.sleep(0.5)
        await self.s.write_to_nordic(Nd.GROUP_ADD.value)

        yesno = YesNoPrompt()
        confirm = await yesno.current_prompt(
            prompt_="Did the shade jog? <y/n> "
        )
        if confirm:
            info("Shade connected")
        else:
            warn("Shade not connected. Please retry.")


def main():
    use_asyncio_event_loop()

    argparser = ArgumentParser()
    argparser.add_argument("--port", help="Dongle serial port", default=None)
    argparser.add_argument(
        "--loglevel",
        default=30,
        help="Set a custom loglevel. default s 30 debug is 10",
        type=int,
    )
    argparser.add_argument("--verbose", action="store_true", default=False)
    args = argparser.parse_args()

    logging.basicConfig(level=args.loglevel)

    set_verbosity(args.verbose)
    loop = asyncio.get_event_loop()

    _main = None
    try:
        _main = MainMenu(loop, args.port, args.verbose)
        loop.run_until_complete(_main.current_prompt())
    except QuitException:
        print("closing pv toolkit")


if __name__ == "__main__":
    main()
