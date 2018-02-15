import asyncio
import aiohttp

from typing import List
from aiopvapi.helpers.aiorequest import PvApiError, AioRequest
from aiopvapi.helpers.constants import ATTR_NAME_UNICODE, ATTR_ID
from aiopvapi.shades import Shades as PvShades, ATTR_SHADE_DATA
from aiopvapi.scenes import Scenes as PvScenes, ATTR_SCENE_DATA
from aiopvapi.rooms import Rooms as PvRooms, ATTR_ROOM_DATA
from aiopvapi.resources.shade import Shade as PvShade
from aiopvapi.resources.scene import Scene as PvScene

from functools import wraps
from nmb.NetBIOS import NetBIOS
from prompt_toolkit import prompt, print_formatted_text, HTML

from prompt_toolkit.contrib.completers import WordCompleter

NETBIOS_HUB2_NAME = 'PowerView-Hub'
# todo: get the proper hub1 netbios name.
NETBIOS_HUB1_NAME = 'hub'


class QuitException(Exception):
    pass


class BackException(Exception):
    pass


def print_key_values(key, value):
    print_formatted_text(
        HTML('  <green>{:<15}</green><orange>{}</orange>'.format(key, value)))


def info(text):
    print_formatted_text(
        HTML('  <green>{}</green>'.format(text))
    )


def warn(text):
    print_formatted_text(
        HTML('  <ansired>{}</ansired>'.format(text)))


def coro(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            val = self.loop.run_until_complete(func(self, *args, **kwargs))
            # self.loop.stop()
            return val
        except PvApiError as err:
            warn("PROBLEM SENDING OUT COMMAND.")

    return wrapper


class BasePrompt:
    def __init__(self, commands=None, loop=None):
        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.get_event_loop()
        self._prompt = "Enter a command: "
        self._commands = {'q': self.quit, 'b': self.back}
        if commands:
            self.register_commands(commands)
        self._auto_return = False

    @property
    def commands(self):
        return self._commands

    def _toolbar_string(self):
        _str = ' | '.join(
            ('({}) {}'.format(key, value.__name__) for key, value in
             self._commands.items()))
        return _str

    def register_commands(self, commands: dict):
        self._commands.update(commands)

    def current_prompt(self, prompt_=None, toolbar=None, autocomplete=None,
                       autoreturn=False):
        """The currently active prompt.

        """
        self._auto_return = autoreturn
        if toolbar is not None:
            self._toolbar_string = lambda: toolbar
        if prompt_ is None:
            prompt_ = self._prompt
        try:
            while True:
                _command = prompt(prompt_,
                                  bottom_toolbar=self._toolbar_string(),
                                  completer=autocomplete)
                _meth = self.commands.get(_command)
                if _meth:
                    val = _meth(self, _command)
                    if val:
                        _command = val
                if self._auto_return:
                    return _command
        except BackException:
            return None

    def back(self, *args, **kwargs):
        raise BackException()

    def quit(self, *args, **kwargs):
        raise QuitException()


class PvPrompt(BasePrompt):
    def __init__(self, request: AioRequest = None, loop=None, commands=None):
        super().__init__(commands=commands, loop=loop)
        self.request = request

        if request:
            self.hub_ip = request.hub_ip
        else:
            self.hub_ip = 'not connected'
        self._raw = {}
        self._id_suggestions = None

    def _populate_id_suggestions(self):
        self._id_suggestions = WordCompleter(
            [str(ids[ATTR_ID]) for ids in self._raw])

    def _print_raw_data(self):
        print("")
        for _item in self._raw:
            print_key_values(_item[ATTR_NAME_UNICODE],
                             _item[ATTR_ID])
        print("")
        info('{} items found.'.format(len(self._raw)))
        print("")

    def _toolbar_string(self):
        line1 = super()._toolbar_string()
        return line1 + ' \nhub: {}'.format(self.hub_ip)

    def find_by_id(self, id_: int):
        for _shade in self._raw:
            if _shade[ATTR_ID] == id_:
                return _shade
        raise InvalidIdException("No data found for id {}".format(id_))

    def _validate_id(self, id):
        if id is None:
            raise InvalidIdException
        try:
            id = int(id)
            return self.find_by_id(id)
        except ValueError:
            raise InvalidIdException('Incorrect ID.')


class Shade(PvPrompt):
    def __init__(self, raw_shade_data, request):
        super().__init__(request, loop=None)
        self._shade = PvShade(raw_shade_data, request)
        self._prompt = 'shade {} {}: '.format(self._shade.id, self._shade.name)
        self.register_commands(
            {'j': self.jog, 'o': self.open, 'c': self.close})

    @coro
    async def jog(self, *args, **kwargs):
        await self._shade.jog()

    @coro
    async def open(self, *args, **kwargs):
        await self._shade.open()

    @coro
    async def close(self, *args, **kwargs):
        await self._shade.close()


# todo: finish this.
class Scenes(PvPrompt):
    def __init__(self, request):
        super().__init__(request)
        self._scenes_resource = PvScenes(request)
        self.register_commands(
            {'l': self.list_scenes, 'a': self.activate_scene})

    @coro
    async def list_scenes(self, *args, **kwargs):
        info("Getting scenes...")
        self._raw = (await self._scenes_resource.get_resources()).get(
            ATTR_SCENE_DATA)
        self._print_raw_data()
        self._populate_id_suggestions()

    @coro
    async def activate_scene(self, *args, **kwargs):
        base_prompt = BasePrompt()
        try:
            _raw = self._validate_id(
                base_prompt.current_prompt(
                    "Select a scene id: ",
                    toolbar="Enter a scene ID.",
                    autoreturn=True,
                    autocomplete=self._id_suggestions)
            )
            _scene = PvScene(_raw, self.request)
            await _scene.activate()
        except InvalidIdException as err:
            warn(err)


class InvalidIdException(Exception):
    pass


class Rooms(PvPrompt):
    def __init__(self, request):
        super().__init__(request)
        self._rooms_resource = PvRooms(request)
        self.register_commands({'l': self.list_rooms})
        self._prompt = "Rooms: "

    @coro
    async def list_rooms(self, *args, **kwargs):
        info("getting rooms")
        self._raw = (await self._rooms_resource.get_resources()).get(
            ATTR_ROOM_DATA)
        self._print_raw_data()
        self._populate_id_suggestions()


class Shades(PvPrompt):
    def __init__(self, request):
        super().__init__(request)
        self._shades_resource = PvShades(request)
        self.register_commands({'l': self.list_shades,
                                's': self.select_shade})
        self._prompt = "Shades: "

    @coro
    async def list_shades(self, *args, **kwargs):
        info("getting shades...")
        self._raw = (await self._shades_resource.get_resources()).get(
            ATTR_SHADE_DATA)
        self._print_raw_data()
        self._populate_id_suggestions()

    def select_shade(self, *args, **kwargs):
        base_prompt = BasePrompt()
        try:
            _raw = self._validate_id(
                base_prompt.current_prompt(
                    "Select a shade id: ",
                    toolbar="Enter a shade id.",
                    autoreturn=True,
                    autocomplete=self._id_suggestions))

            shade = Shade(_raw, self.request)
            shade.current_prompt()
        except InvalidIdException as err:
            warn(err)


class Discovery(BasePrompt):
    def __init__(self):
        super().__init__()
        self._prompt = "Hub connection: "
        self.register_commands({'d': self.discover, 'c': self.connect})
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
        self._auto_return = True  # Exits the prompt loop.
        pr = BasePrompt()
        ip = pr.current_prompt(
            'Enter ip address: ',
            toolbar='Enter a valid ip address: 129.168.2.3',
            autoreturn=True,
            autocomplete=self._ip_completer
        )
        try:
            self.validate_ip(ip)
        except ValueError:
            warn("Invalid ip entered.")
        else:
            self._auto_return = True  # Exits the prompt loop.
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


class MainMenu(PvPrompt):
    def __init__(self, loop, hub=None):
        self.loop = loop
        super().__init__()
        self.register_commands({'c': self.connect_to_hub})
        if hub:
            self._register_hub_commands()
        self._prompt = "PowerView toolkit: "

    def _register_hub_commands(self):
        self.register_commands({'s': self.shades,
                                'e': self.scenes,
                                'r': self.rooms})

    def connect_to_hub(self, *args, **kwargs):
        discovery = Discovery()
        hub = discovery.current_prompt()
        if hub:
            info("Using {} as the PowerView hub ip address.".format(hub))
            self.request = AioRequest(hub, loop=self.loop)
            self._register_hub_commands()

    def shades(self, *args, **kwargs):
        shade = Shades(self.request)
        shade.current_prompt()

    def scenes(self, *args, **kwargs):
        scene = Scenes(self.request)
        scene.current_prompt()

    def rooms(self, *args, **kwargs):
        rooms = Rooms(self.request)
        rooms.current_prompt()

    def close(self):
        if self.request:
            self.loop.run_until_complete(self.request.websession.close())


def main():
    _main = None
    loop = asyncio.get_event_loop()
    try:
        _main = MainMenu(loop)
        _main.current_prompt()
        # my_tool(loop, session)
    except QuitException:
        print("closing pv toolkit")
    finally:
        _main.close()
