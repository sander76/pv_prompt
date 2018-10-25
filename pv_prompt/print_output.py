import asyncio
import json
import logging
from asyncio import CancelledError
from typing import TYPE_CHECKING, Iterable

import pygments
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.formatted_text import PygmentsTokens
from pygments.lexers.data import JsonLexer

from pv_prompt.helpers import VERBOSE

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pv_prompt.resource_cache import ResourceCache


def print_key_values(key, value):
    print_formatted_text(
        HTML("  <green>{:<15}</green><orange>{}</orange>".format(key, value))
    )


def print_table(*values):
    _columns = len(values)
    # _first = '  <green>{:<15}</green>'
    # _second = '<orange>{:<15}</orange>' * (_columns - 1)
    _full = "  <green>{:<15}</green>" + "<orange>{:<15}</orange>" * (_columns - 1)
    print_formatted_text(HTML(_full.format(*values)))


def print_tabbed_data(*row):
    _columns = len(row)


def info(text, **kwargs):
    print_formatted_text(HTML("  <green>{}</green>".format(text)), **kwargs)


def spinner():
    print_formatted_text(HTML("<orange>.</orange>"), end="")


def warn(text):
    print_formatted_text(HTML("  <ansired>{}</ansired>".format(text)))


def print_waiting_done(action):
    async def waiting():
        info(action, end="")
        try:
            while True:
                await asyncio.sleep(0.5)
                spinner()
        except CancelledError:
            pass

    task = asyncio.ensure_future(waiting())

    async def _finished():
        info("done")
        # todo: make the wile loop not infinite as it might hang indefinitely
        task.cancel()
        while not task.cancelled:
            await asyncio.sleep(0.5)

    return _finished


def print_dict(data: dict):
    tokens = list(pygments.lex(json.dumps(data, indent=4), lexer=JsonLexer()))
    print_formatted_text(PygmentsTokens(tokens))


def print_scenes(scenes: "ResourceCache", rooms):
    LOGGER.debug("verbose: %s", VERBOSE)
    if VERBOSE():
        print("")
        for itm in scenes.resources:
            print_dict(itm._raw_data)
    print("")
    LOGGER.debug("printing scenes")
    print_table("NAME", "ID", "ROOM", "NETWORK_ID")
    print_table("----", "--", "----", "----------")
    tbl = [
        (
            _item.name,
            _item.id,
            rooms.get_name_by_id(_item.room_id),
            _item._raw_data["networkNumber"],
        )
        for _item in scenes.resources
    ]
    tbl.sort(key=lambda x: x[-1])

    for _ln in tbl:
        print_table(*_ln)
    print_length(len(scenes.resources))


def print_shade_data(shades: Iterable):
    """Prints a list of shades.
    """
    if VERBOSE():
        print("")
        for itm in shades:
            print_dict(itm._raw_data)
    print_table("NAME", "ID", "TYPE")
    print_table("----", "--", "----")
    count = 0
    LOGGER.debug(shades)
    for _item in shades:
        count += 1
        print_table(_item.name, _item.id, _item.shade_type.description)
    print_length(count)


def print_resource_data(resource):
    print("")
    print_table("NAME", "ID")
    print_table("----", "--")
    for _item in resource.resources:
        print_table(_item.name, _item.id)
    print_length(len(resource.resources))


def print_length(length):
    print("")
    info("{} items found.".format(length))
    print("")
