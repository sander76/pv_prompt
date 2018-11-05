import logging
from argparse import ArgumentParser

from aiopvapi.helpers.aiorequest import AioRequest
from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop

from pv_prompt.print_output import print_dict
from pv_prompt.base_prompts import BasePrompt, PvPrompt, QuitException, Command
from pv_prompt.discovery import Discovery
from pv_prompt.helpers import get_loop, set_verbosity, VERBOSE
from pv_prompt.print_output import info, print_resource_data, print_key_values
from pv_prompt.resource_cache import HubCache
from pv_prompt.scenes import Scenes
from pv_prompt.shades import Shades

# todo: get the proper hub1 netbios name.

LOGGER = logging.getLogger(__name__)


class Rooms(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.rooms
        self.register_commands({"l": Command(function_=self.list_rooms)})
        self._prompt = "Rooms: "

    async def list_rooms(self, *args, **kwargs):
        info("getting rooms")
        print_resource_data(self.hub_cache.rooms)


class MainMenu(BasePrompt):
    def __init__(self, loop, hub=None, verbose=False):
        self.loop = loop
        super().__init__()
        self.request = None
        self.hub_cache = None
        self.register_commands(
            {
                "c": Command(function_=self._connect_to_hub),
                "v": Command(function_=self._toggle_verbose),
            }
        )
        if hub:
            self._register_hub_commands()
            self.request = AioRequest(hub, loop=self.loop)
            self.hub_cache = HubCache(self.request, self.loop)

        self._prompt = "PowerView toolkit: "

    def _register_hub_commands(self):
        self.register_commands(
            {
                "s": Command(function_=self.shades),
                "e": Command(function_=self.scenes),
                "r": Command(function_=self.rooms),
            }
        )

    async def current_prompt(
        self,
        prompt_=None,
        toolbar=None,
        autocomplete=None,
        autoreturn=False,
        default="",
    ):
        if self.hub_cache:
            await self.hub_cache.update()
        await super().current_prompt()

    async def _toggle_verbose(self, *args, **kwargs):
        set_verbosity(not VERBOSE())

        print_key_values("Verbosity", "on" if VERBOSE() else "off")

    async def _connect_to_hub(self, *args, **kwargs):
        discovery = Discovery()
        hub = await discovery.current_prompt()
        LOGGER.debug("received hub ip: {}".format(hub))
        if hub:
            info("Using {} as the PowerView hub ip address.".format(hub))
            self.request = AioRequest(hub, loop=self.loop)
            self._register_hub_commands()
            self.hub_cache = HubCache(self.request)
            await self.hub_cache.update()
            print_dict(self.hub_cache.user_data._raw)
            # async def answer_no(*args, **kwargs):
            #     LOGGER.debug("No entered.")
            #
            # async def answer_yes(*args, **kwargs):
            #     LOGGER.debug("Yes entered.")
            #     await self.hub_cache(*args, **kwargs)
            #
            # pr = BasePrompt(
            #     commands={
            #         "y": Command(function_=answer_yes, autoreturn=True),
            #         "n": Command(function_=answer_no, autoreturn=True),
            #     }
            # )
            # await pr.current_prompt(prompt_="Query the hub ? <y/n> ")

    # async def update_hub_cache(self, *args, **kwargs):
    #     LOGGER.debug("Querying the hub.")
    #
    #     # self._hub_cache.verbose=self.verbose
    #     await self.hub_cache.update()

    async def shades(self, *args, **kwargs):
        shade = Shades(self.request, self.hub_cache)
        await shade.current_prompt()

    async def scenes(self, *args, **kwargs):
        scene = Scenes(self.request, self.hub_cache)
        await scene.current_prompt()

    async def rooms(self, *args, **kwargs):
        rooms = Rooms(self.request, self.hub_cache)
        await rooms.current_prompt()

    def close(self):
        if self.request:
            self.loop.run_until_complete(self.request.websession.close())


def main():
    use_asyncio_event_loop()

    argparser = ArgumentParser()
    argparser.add_argument(
        "--hubip", help="The ip address of the hub", default=None
    )
    argparser.add_argument(
        "--loglevel",
        default=30,
        help="Set a custom loglevel. default s 30 debug is 10",
        type=int,
    )
    argparser.add_argument(
        "--verbose",
        help="Verbose output on hub feedback",
        action="store_true",
        default=False,
    )
    args = argparser.parse_args()
    logging.basicConfig(level=args.loglevel)

    set_verbosity(args.verbose)
    loop = get_loop()
    _main = None
    try:
        _main = MainMenu(loop, args.hubip, args.verbose)
        loop.run_until_complete(_main.current_prompt())
    except QuitException:
        print("closing pv toolkit")
    finally:
        if _main:
            _main.close()


if __name__ == "__main__":
    main()
