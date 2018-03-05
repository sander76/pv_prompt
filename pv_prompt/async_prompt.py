import asyncio
import logging
from argparse import ArgumentParser

from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.resources.scene import Scene as PvScene
from aiopvapi.resources.shade import BaseShade
from aiopvapi.scene_members import SceneMembers
from nmb.NetBIOS import NetBIOS
from prompt_toolkit.contrib.completers import WordCompleter

from pv_prompt.base_prompts import BasePrompt, PvPrompt, PvResourcePrompt, \
    InvalidIdException, QuitException, Command
from pv_prompt.helpers import coro
from pv_prompt.print_output import info, print_scenes, warn, print_shade_data, \
    print_resource_data, print_key_values
from pv_prompt.resource_cache import HubCache

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
             'r': Command(function_=self.refresh)})

    @coro
    async def refresh(self, *args, **kwargs):
        await self.pv_resource.refresh()

    @coro
    async def jog(self, *args, **kwargs):
        await self.pv_resource.jog()

    @coro
    async def open(self, *args, **kwargs):
        await self.pv_resource.open()

    @coro
    async def close(self, *args, **kwargs):
        await self.pv_resource.close()


class Scenes(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.scenes
        self.register_commands(
            {'l': Command(function_=self.list_scenes),
             'a': Command(function_=self.activate_scene),
             's': Command(function_=self.select_scene)})

    @coro
    async def list_scenes(self, *args, **kwargs):
        info("Getting scenes...")
        print_scenes(self.hub_cache.scenes, self.hub_cache.rooms)

    @coro
    async def activate_scene(self, *args, **kwargs):
        try:
            _scene = self.hub_cache.scenes.select_resource()
            await _scene.activate()
        except InvalidIdException as err:
            warn(err)

    def select_scene(self, *args, **kwargs):
        try:
            pv_scene = self.hub_cache.scenes.select_resource()
            scene = Scene(pv_scene, self.request, self.hub_cache)
            scene.current_prompt()
        except InvalidIdException as err:
            warn(err)


class Scene(PvResourcePrompt):
    def __init__(self, scene: PvScene, request, hub_cache):
        super().__init__(scene, request, hub_cache)
        self._prompt = 'scene {} {}:'.format(scene.id, scene.name)
        self.register_commands(
            {'a': Command(function_=self.add_shade_to_scene)})

    @coro
    async def add_shade_to_scene(self, *args, **kwargs):
        shade = self.hub_cache.shades.select_resource()
        _position = await shade.get_current_position()
        if _position:
            await (SceneMembers(self.request)).create_scene_member(
                _position, self.api_resource.id, shade.id)
        info('Scene created.')

    @coro
    async def show_members(self, *args, **kwargs):
        info("getting scene members")
        _scene_members = self.hub_cache.scene_members.re


class Rooms(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.rooms
        self.register_commands({'l': Command(function_=self.list_rooms)})
        self._prompt = "Rooms: "

    @coro
    async def list_rooms(self, *args, **kwargs):
        info("getting rooms")
        print_resource_data(self.hub_cache.rooms)


class Shades(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        # self._shades_resource = PvShades(request)
        self.api_resource = hub_cache.shades
        self.register_commands({'l': Command(function_=self.list_shades),
                                's': Command(function_=self.select_shade)})
        self._prompt = "Shades: "

    @coro
    async def list_shades(self, *args, **kwargs):
        info("getting shades...")
        print_shade_data(self.hub_cache.shades)

    def select_shade(self, *args, **kwargs):
        try:
            pv_shade = self.hub_cache.shades.select_resource()
            shade = Shade(pv_shade, self.request, self.hub_cache)
            shade.current_prompt()
        except InvalidIdException as err:
            warn(err)


class Discovery(BasePrompt):
    def __init__(self):
        super().__init__()
        self._prompt = "Hub connection: "
        self.register_commands(
            {'d': Command(function_=self.discover),
             'c': Command(function_=self.connect, autoreturn=True)})
        self._ip_suggestions = None
        self._ip_completer = None

    def discover(self, *args, **kwargs):
        nb = NetBIOS()
        info('Discovering hubs...')
        self._ip_suggestions = nb.queryName(NETBIOS_HUB2_NAME, timeout=5)
        if self._ip_suggestions:
            for _hub in self._ip_suggestions:
                print_key_values('hub2', _hub)
            self._populate_completer()
        else:
            warn("...Discovery timed out")

    def _populate_completer(self):
        self._ip_completer = WordCompleter(self._ip_suggestions)

    def connect(self, *args, **kwargs):
        pr = BasePrompt()
        ip = pr.current_prompt(
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
        self.register_commands({'c': Command(function_=self.connect_to_hub)})
        if hub:
            self._register_hub_commands()
        self._prompt = "PowerView toolkit: "
        self._hub_cache = None

    def _register_hub_commands(self):
        self.register_commands({'s': Command(function_=self.shades),
                                'e': Command(function_=self.scenes),
                                'r': Command(function_=self.rooms),
                                'h': Command(function_=self.hub_cache)})

    def connect_to_hub(self, *args, **kwargs):
        discovery = Discovery()
        hub = discovery.current_prompt()
        LOGGER.debug("received hub ip: {}".format(hub))
        if hub:
            info("Using {} as the PowerView hub ip address.".format(hub))
            self.request = AioRequest(hub, loop=self.loop)
            self._register_hub_commands()
            self._hub_cache = HubCache(self.request)

            def answer_no(*args, **kwargs):
                LOGGER.debug('No entered.')

            def answer_yes(*args, **kwargs):
                LOGGER.debug('Yes entered.')
                self.hub_cache(*args, **kwargs)

            pr = BasePrompt(
                commands={'y': Command(function_=answer_yes, autoreturn=True),
                          'n': Command(function_=answer_no, autoreturn=True)})
            pr.current_prompt(
                prompt_='Query the hub ? <y/n> ')

    def hub_cache(self, *args, **kwargs):
        LOGGER.debug('Querying the hub.')
        self._hub_cache.update()

    def shades(self, *args, **kwargs):
        shade = Shades(self.request, self._hub_cache)
        shade.current_prompt()

    def scenes(self, *args, **kwargs):
        scene = Scenes(self.request, self._hub_cache)
        scene.current_prompt()

    def rooms(self, *args, **kwargs):
        rooms = Rooms(self.request, self._hub_cache)
        rooms.current_prompt()

    def close(self):
        if self.request:
            self.loop.run_until_complete(self.request.websession.close())


# logging.basicConfig(level=logging.DEBUG)


def main():
    argparser = ArgumentParser()
    argparser.add_argument(
        '--hubip', help="The ip address of the hub", default=None)
    argparser.add_argument(
        '--loglevel', default=30,
        help="Set a custom loglevel. default s 30 debug is 10", type=int)
    args = argparser.parse_args()
    logging.basicConfig(level=args.loglevel)

    loop = asyncio.get_event_loop()
    try:
        _main = MainMenu(loop, args.hubip)
        _main.current_prompt()
        # my_tool(loop, session)
    except QuitException:
        print("closing pv toolkit")
    finally:
        _main.close()
