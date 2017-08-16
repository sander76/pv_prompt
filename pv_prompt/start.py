import logging

import asyncio
import pprint

from prompt_toolkit import prompt_async

from pv_prompt.command_options import CommandOptions, CommandOption
from .powerview import PowerView

KEY_BACK = 'b'
KEY_QUIT = 'q'

NAV_SHADES = CommandOption('s', '(s)hades')
NAV_ROOMS = CommandOption('r', '(r)ooms')
NAV_SCENES = CommandOption('e', 'sc(e)nes')
NAV_EXIT = CommandOption('q', '(q)uit')

MAIN_OPTIONS = CommandOptions(
    NAV_SHADES,
    NAV_ROOMS,
    NAV_SCENES,
    NAV_EXIT
)

COMMAND_LIST_SHADES = CommandOption('l', '(l)list shades')
CMD_SELECT_SHADE = CommandOption('s', '(s)select shade')

SHADES_COMMANDS = CommandOptions(
    COMMAND_LIST_SHADES,
    CMD_SELECT_SHADE
)

CMD_SHADE_DATA = CommandOption('s', '(s)hade data')
SHADE_COMMANDS = CommandOptions(
    CMD_SHADE_DATA
)

COMMAND_LIST_ROOMS = CommandOption('l', '(l)ist rooms')
COMMAND_DELETE_ROOM = CommandOption('d', '(d)elete room')

ROOM_COMMANDS = CommandOptions(
    COMMAND_LIST_ROOMS,
    COMMAND_DELETE_ROOM
)

CMD_LIST_SCENES = CommandOption('l', '(l)ist scenes')
CMD_DELETE_SCENE = CommandOption('d', '(d)elete scene')
CMD_ADD_SHADE_TO_SCENE = CommandOption('a', '(a)dd shade to scene')

SCENE_COMMANDS = CommandOptions(
    CMD_LIST_SCENES,
    CMD_DELETE_SCENE
)


def do_prompt(func):
    async def wrapper(self, prompt, options=None, **kwargs):

        while True:
            if options:
                options.print_options()
            result = await prompt_async(prompt)
            if result == KEY_BACK or result == KEY_QUIT:
                return result
            result = await func(self, result, **kwargs)
            if result == KEY_BACK:
                pass
            if result == KEY_QUIT:
                return result

    return wrapper


class PowerViewPrompt(PowerView):
    def __init__(self, hub_ip, loop, session):
        PowerView.__init__(self, hub_ip, loop, session)

    @do_prompt
    async def cmd_delete_scene(self, result):
        try:
            result = int(result)
            _data = await self.delete_scene(result)
            pprint.pprint(_data)
        except ValueError:
            print('Error: The id should be a number.')
        return result

    @do_prompt
    async def cmd_delete_room(self, result):
        try:
            result = int(result)
            _data = await self.delete_room(result)
            pprint.pprint(_data)
        except ValueError:
            print('Error: The id should be a number')
        return result

    @do_prompt
    async def rooms(self, result):
        # result = None
        #ROOM_COMMANDS.print_options()
        # while not result == KEY_BACK and not result == KEY_QUIT:
        #    result = await prompt_async('ROOMS:> ')
        if result == COMMAND_LIST_ROOMS.key:
            await self.print_rooms()
        if result == COMMAND_DELETE_ROOM.key:
            result = await self.cmd_delete_room('Enter room id:')
        return result

    @do_prompt
    async def scenes(self, result):
        if result == CMD_LIST_SCENES.key:
            _data = await self.get_scenes()
            pprint.pprint(_data)
        elif result == CMD_DELETE_SCENE.key:
            result = await self.cmd_delete_scene('Enter Scene id > ')
        return result

    @do_prompt
    async def shade(self, result, active_id=None):
        if result == CMD_SHADE_DATA.key:
            _shade = await self.get_shade(active_id)
            if _shade:
                await _shade.refresh()
                print(_shade.raw_data)

        return result

    @do_prompt
    async def select_shade(self, result):
        try:
            _val = int(result)
            result = await self.shade('Shade {} > '.format(_val),
                                      options=SHADE_COMMANDS,
                                      active_id=_val)
        except ValueError:
            print('Erorr: The id should be a number.')
        return result

    @do_prompt
    async def shades(self, result):
        if result == COMMAND_LIST_SHADES.key:
            _data = await self.get_shades()
            pprint.pprint(_data)
        elif result == CMD_SELECT_SHADE.key:
            result = await self.select_shade('Enter shadeid > ')

        return result

    async def my_coroutine(self):
        while True:
            MAIN_OPTIONS.print_options()
            result = await prompt_async('choose a command:> ',
                                        patch_stdout=True)
            # print('result is {}'.format(result))
            if result == NAV_SHADES.key:
                result = await self.shades("Shades >", SHADES_COMMANDS)
            elif result == NAV_ROOMS.key:
                result = await self.rooms("Rooms:> ", ROOM_COMMANDS)
            elif result == NAV_SCENES.key:
                result = await self.scenes("Scenes > ", SCENE_COMMANDS)
            if result == KEY_QUIT:
                break
