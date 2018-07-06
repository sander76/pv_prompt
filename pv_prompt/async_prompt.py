import logging
from argparse import ArgumentParser

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.resources.shade import BaseShade
from nmb.NetBIOS import NetBIOS
from prompt_toolkit.completion import WordCompleter

from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop

from pv_prompt.base_prompts import BasePrompt, PvPrompt, PvResourcePrompt, \
    InvalidIdException, QuitException, Command
from pv_prompt.helpers import get_loop
from pv_prompt.print_output import info, warn, print_shade_data, \
    print_resource_data, print_key_values, print_waiting_done, print_table
from pv_prompt.resource_cache import HubCache
from pv_prompt.scenes import Scenes
from pv_prompt.zero_conf import Zero

NETBIOS_HUB2_NAME = 'PowerView-Hub'
# todo: get the proper hub1 netbios name.
NETBIOS_HUB1_NAME = 'hub'

LOGGER = logging.getLogger(__name__)


# class ShadeResourceCache(ResourceCache):
#
#     def print_resource_data(self):
#         print("")
#         print_table('NAME', 'ID', 'TYPE')
#         print_table('----', '--', '----')
#         for _item in self.resources:
#             print_table(_item.name, _item.id, _item.shade_type.description)
#         self.print_length()
#         print("")
#
#
# class SceneMemberResourceCache(ResourceCache):
#     def __init__(self, api_entry_point: ApiEntryPoint,
#                  resource_type_name: str,
#                  request: AioRequest,
#                  shades: ShadeResourceCache,
#                  scenes: ResourceCache):
#         super().__init__(api_entry_point,
#                          resource_type_name,
#                          request)
#         self.shades = shades
#         self.scenes = scenes
#
#     def print_resource_data(self):
#         print("")
#         print_table('SHADE', 'SCENE')
#         for _item in self.resources:
#             _shade = self.shades.get_name_by_id(_item.shade_id)
#             _scene = self.scenes.get_name_by_id(_item.scene_id)
#             print_table(_shade.name, _scene.name)
#         self.print_length()


class Shade(PvResourcePrompt):
    def __init__(self, shade: BaseShade, request, hub_cache):
        super().__init__(shade, request, hub_cache)
        self._prompt = 'shade {} {}: '.format(shade.id, shade.name)
        self.register_commands(
            {'j': Command(function_=self.jog, label='(j)og'),
             'o': Command(function_=self.open),
             'c': Command(function_=self.close),
             'r': Command(function_=self.refresh),
             's': Command(function_=self.stop)})

    async def refresh(self, *args, **kwargs):
        await self.pv_resource.refresh()

    async def jog(self, *args, **kwargs):
        await self.pv_resource.jog()

    async def open(self, *args, **kwargs):
        await self.pv_resource.open()

    async def close(self, *args, **kwargs):
        await self.pv_resource.close()

    async def stop(self, *args, **kwargs):
        await self.pv_resource.stop()


class Rooms(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.rooms
        self.register_commands({'l': Command(function_=self.list_rooms)})
        self._prompt = "Rooms: "

    async def list_rooms(self, *args, **kwargs):
        info("getting rooms")
        print_resource_data(self.hub_cache.rooms)


class Shades(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        # self._shades_resource = PvShades(request)
        self.api_resource = hub_cache.shades
        self.register_commands(
            {'l': Command(function_=self._list_shades),
             's': Command(function_=self._select_shade)})
        self._prompt = "Shades: "

    async def _list_shades(self, *args, **kwargs):
        info("getting shades...")
        print_shade_data(self.hub_cache.shades)

    async def _select_shade(self, *args, **kwargs):
        try:
            pv_shade = await self.hub_cache.shades.select_resource()
            shade = Shade(pv_shade, self.request, self.hub_cache)
            await shade.current_prompt()
        except InvalidIdException as err:
            warn(err)


class Discovery(BasePrompt):
    def __init__(self):
        super().__init__()
        self._prompt = "Hub connection: "
        self.register_commands(
            {'d': Command(function_=self._discover),
             'c': Command(function_=self.connect, autoreturn=True)})
        self._ip_suggestions = None
        self._ip_completer = None

    async def _discover(self, *args, **kwargs):
        self._ip_suggestions = []
        zero = Zero(self.loop)
        done = print_waiting_done('Discovering hubs')
        LOGGER.debug("discover command fire")
        await zero.discover()
        LOGGER.debug("discovery done")
        await done()
        if zero.hubs:
            self.print_hub_table()
            for _hub in zero.hubs:
                print_key_values(_hub.name, _hub.ip)
                self._ip_suggestions.append(_hub.ip)
        self._populate_completer()

    async def _discover_hub1(self, *args, **kwargs):
        nb = NetBIOS()
        info('Discovering hubs...')
        LOGGER.debug("discover command fire")
        self._ip_suggestions = nb.queryName(NETBIOS_HUB1_NAME, timeout=5)
        if self._ip_suggestions:
            self.print_hub_table()
            for _hub in self._ip_suggestions:
                print_table('hub1', _hub)
            self._populate_completer()
        else:
            warn("...Discovery timed out")

    def print_hub_table(self):
        print('')
        print_table('NAME', 'IP ADDRESS')
        print_table('----', '----------')

    def _populate_completer(self):
        self._ip_completer = WordCompleter(self._ip_suggestions)

    async def connect(self, *args, **kwargs):
        pr = BasePrompt()
        ip = await pr.current_prompt(
            'Enter ip address: ',
            toolbar='Enter a valid ip address: 129.168.2.3',
            autoreturn=True,
            autocomplete=self._ip_completer
        )
        LOGGER.debug('entered ip is : {}'.format(ip))
        try:
            self.validate_ip(ip)
        except ValueError:
            warn("Invalid ip entered.")
        else:
            LOGGER.debug("returning ip address: {}".format(ip))
            return 'http://{}'.format(ip)

    def validate_ip(self, ip):
        vals = ip.split('.')
        try:
            ints = (int(val) for val in vals)
        except ValueError:
            raise ValueError
        for _int in ints:
            if _int < 0 or _int > 256:
                raise ValueError


class MainMenu(BasePrompt):
    def __init__(self, loop, hub=None):
        self.loop = loop
        super().__init__()
        self.request = None
        self.register_commands({'c': Command(function_=self._connect_to_hub)})
        if hub:
            self._register_hub_commands()
            self.request = AioRequest(hub, loop=self.loop)
        self._prompt = "PowerView toolkit: "
        self._hub_cache = None

    def _register_hub_commands(self):
        self.register_commands(
            {'s': Command(function_=self.shades),
             'e': Command(function_=self.scenes),
             'r': Command(function_=self.rooms),
             'h': Command(function_=self.hub_cache)})

    async def _connect_to_hub(self, *args, **kwargs):
        discovery = Discovery()
        hub = await discovery.current_prompt()
        LOGGER.debug("received hub ip: {}".format(hub))
        if hub:
            info("Using {} as the PowerView hub ip address.".format(hub))
            self.request = AioRequest(hub, loop=self.loop)
            self._register_hub_commands()


            async def answer_no(*args, **kwargs):
                LOGGER.debug('No entered.')

            async def answer_yes(*args, **kwargs):
                LOGGER.debug('Yes entered.')
                await self.hub_cache(*args, **kwargs)

            pr = BasePrompt(
                commands={'y': Command(function_=answer_yes, autoreturn=True),
                          'n': Command(function_=answer_no, autoreturn=True)})
            await pr.current_prompt(
                prompt_='Query the hub ? <y/n> ')

    async def hub_cache(self, *args, **kwargs):
        LOGGER.debug('Querying the hub.')
        self._hub_cache = HubCache(self.request)
        await self._hub_cache.update()

    async def shades(self, *args, **kwargs):
        shade = Shades(self.request, self._hub_cache)
        await shade.current_prompt()

    async def scenes(self, *args, **kwargs):
        scene = Scenes(self.request, self._hub_cache)
        await scene.current_prompt()

    async def rooms(self, *args, **kwargs):
        rooms = Rooms(self.request, self._hub_cache)
        await rooms.current_prompt()

    def close(self):
        if self.request:
            self.loop.run_until_complete(self.request.websession.close())



def main():
    use_asyncio_event_loop()

    argparser = ArgumentParser()
    argparser.add_argument(
        '--hubip', help="The ip address of the hub", default=None)
    argparser.add_argument(
        '--loglevel', default=30,
        help="Set a custom loglevel. default s 30 debug is 10", type=int)
    args = argparser.parse_args()
    logging.basicConfig(level=args.loglevel)

    loop = get_loop()
    try:
        _main = MainMenu(loop, args.hubip)
        loop.run_until_complete(_main.current_prompt())
    except QuitException:
        print("closing pv toolkit")
    finally:
        _main.close()
