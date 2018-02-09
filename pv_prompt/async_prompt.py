import asyncio
import aiohttp

from typing import List
from aiopvapi.helpers.aiorequest import PvApiError
from aiopvapi.helpers.constants import ATTR_NAME_UNICODE, ATTR_ID
from aiopvapi.shades import Shades as PvShades, ATTR_SHADE_DATA
from functools import wraps
from nmb.NetBIOS import NetBIOS
from prompt_toolkit import prompt, print_formatted_text, HTML
from aiopvapi.resources.shade import Shade as PvShade
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
    def __init__(self, commands=None):
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
    def __init__(self, hub_ip, loop, session, commands=None):
        super().__init__(commands)
        self.hub_ip = hub_ip
        self.loop = loop
        self.session = session

    def _toolbar_string(self):
        line1 = super()._toolbar_string()
        return line1 + ' | {}'.format(self.hub_ip)


class Shade(PvPrompt):
    def __init__(self, raw_shade_data, hub_ip, loop=None, session=None):
        super().__init__(hub_ip, loop, session)

        self._shade = PvShade(raw_shade_data, hub_ip, loop, session)
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


class Shades(PvPrompt):
    def __init__(self, hub_ip, loop=None, session=None):
        super().__init__(hub_ip, loop, session)
        self._shades_resource = PvShades(hub_ip, loop, session)
        self.register_commands({'l': self.list_shades,
                                's': self.select_shade})
        self._prompt = "Shades: "
        self._raw = {}
        self._shade_id_suggestions = None

    def _populate_suggestions(self, shade_ids: List[str]):
        self._shade_id_suggestions = WordCompleter(shade_ids)

    def find_by_id(self, id_: int):
        for _shade in self._raw:
            if _shade[ATTR_ID] == id_:
                return _shade
        return None

    @coro
    async def list_shades(self, *args, **kwargs):
        print("getting shades")
        self._raw = (await self._shades_resource.get_resources()).get(
            ATTR_SHADE_DATA)
        print("")

        for _shade in self._raw:
            print_key_values(_shade[ATTR_NAME_UNICODE],
                             _shade[ATTR_ID])
        self._populate_suggestions(
            [str(ids[ATTR_ID]) for ids in self._raw]
        )

        print("")

    def select_shade(self, *args, **kwargs):
        base_prompt = BasePrompt()
        _id = base_prompt.current_prompt(
            "Select a shade id: ",
            toolbar="Enter a shade id.",
            autoreturn=True,
            autocomplete=self._shade_id_suggestions)
        _shade = None
        if _id is None:
            return
        try:
            _shade = self.find_by_id(int(_id))
        except ValueError:
            warn('Incorrect shade id.')
            return
        if _shade:
            shade = Shade(_shade, self.hub_ip, self.loop, self.session)
            shade.current_prompt()
        else:
            warn("Shade with id: {} not found".format(_id))


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
    def __init__(self, loop, session, hub=None):
        super().__init__(hub, loop, session)
        self.register_commands({'c': self.connect_to_hub})
        if hub:
            self._register_hub_commands()
        self._prompt = "PowerView toolkit: "

    def _register_hub_commands(self):
        self.register_commands({'s': self.shades})

    def connect_to_hub(self, *args, **kwargs):
        discovery = Discovery()
        hub = discovery.current_prompt()
        if hub:
            info("Using {} as the PowerView hub ip address.".format(hub))
            self.hub_ip = hub
            self._register_hub_commands()

    def shades(self, *args, **kwargs):
        shade = Shades(self.hub_ip, self.loop, self.session)
        shade.current_prompt()


def main():
    loop = asyncio.get_event_loop()
    session = aiohttp.ClientSession(loop=loop)
    try:
        _main = MainMenu(loop, session)
        _main.current_prompt()
        # my_tool(loop, session)
    except QuitException:
        print("closing pv toolkit")
    finally:
        session.close()
