import asyncio
import logging
from asyncio import CancelledError
from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text, HTML

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pv_prompt.resource_cache import ResourceCache


def print_key_values(key, value):
    print_formatted_text(
        HTML('  <green>{:<15}</green><orange>{}</orange>'.format(key, value)))


def print_table(*values):
    _columns = len(values)
    # _first = '  <green>{:<15}</green>'
    # _second = '<orange>{:<15}</orange>' * (_columns - 1)
    _full = '  <green>{:<15}</green>' + '<orange>{:<15}</orange>' * (
            _columns - 1)
    print_formatted_text(HTML(_full.format(*values)))


def info(text, **kwargs):
    print_formatted_text(
        HTML('  <green>{}</green>'.format(text)), **kwargs
    )


def spinner():
    print_formatted_text(
        HTML('<orange>.</orange>'), end='')



def warn(text):
    print_formatted_text(
        HTML('  <ansired>{}</ansired>'.format(text)))


def print_waiting_done(action):
    async def waiting():
        info(action, end='')
        try:
            while True:
                await asyncio.sleep(0.5)
                LOGGER.debug("spinning")
                spinner()
        except CancelledError:
            pass


    task = asyncio.ensure_future(waiting())

    async def _finished():
        info('done')
        # todo: make the wile loop not infinite as it might hang indefinitely
        task.cancel()
        while not task.cancelled:
            await asyncio.sleep(0.5)

    return _finished


def print_scenes(scenes: 'ResourceCache', rooms):
    print("")
    LOGGER.debug("printing scenes")
    print_table('NAME', 'ID', 'ROOM')
    print_table('----', '--', '----')
    tbl = [
        (_item.name, _item.id,
         rooms.get_name_by_id(_item.room_id)) for _item in
        scenes.resources
    ]
    tbl.sort(key=lambda x: x[-1])

    for _ln in tbl:
        print_table(*_ln)
    print_length(len(scenes.resources))


def print_shade_data(shades):
    print("")
    print_table('NAME', 'ID', 'TYPE')
    print_table('----', '--', '----')
    for _item in shades.resources:
        print_table(_item.name, _item.id, _item.shade_type.description)
    print_length(len(shades.resources))


# def print_resource_data(scene_members: ResourceCache, shades: ResourceCache,
#                         scenes: ResourceCache):


# print("")
#         print_table('SHADE', 'SCENE')
#         for _item in self.resources:
#             _shade = self.shades.get_name_by_id(_item.shade_id)
#             _scene = self.scenes.get_name_by_id(_item.scene_id)
#             print_table(_shade.name, _scene.name)
#         self.print_length()

def print_resource_data(resource):
    print("")
    print_table('NAME', 'ID')
    print_table('----', '--')
    for _item in resource.resources:
        print_table(_item.name, _item.id)
    print_length(len(resource.resources))


def print_length(length):
    print('')
    info('{} items found.'.format(length))
    print('')
