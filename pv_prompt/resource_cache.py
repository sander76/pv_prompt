import asyncio

from aiopvapi.helpers.aiorequest import AioRequest, PvApiConnectionError
from aiopvapi.helpers.api_base import ApiEntryPoint
from aiopvapi.rooms import Rooms as PvRooms
from aiopvapi.scene_members import SceneMembers as PvSceneMembers
from aiopvapi.scenes import Scenes as PvScenes
from aiopvapi.shades import Shades as PvShades
from aiopvapi.hub import UserData
from prompt_toolkit.completion import WordCompleter

from pv_prompt.base_prompts import BasePrompt, InvalidIdException
from pv_prompt.helpers import get_loop
from pv_prompt.print_output import print_waiting_done

import logging

LOGGER = logging.getLogger(__name__)


class ResourceCache:
    """PowerView resource cache."""

    def __init__(
        self,
        api_entry_point: ApiEntryPoint,
        resource_type_name: str,
        request: AioRequest,
    ):
        self.request = request
        self.api_entry_point = api_entry_point
        self.resources = []
        self.id_suggestions = []
        self.resource_type_name = resource_type_name

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self.resources)

    def get_name_by_id(self, _id):
        for _item in self.resources:
            if _item.id == _id:
                return _item.name

    def _populate_id_suggestions(self):
        self.id_suggestions = WordCompleter([str(_item.id) for _item in self.resources])

    def find_by_id(self, id_: int):
        for _item in self.resources:
            if _item.id == id_:
                return _item
        raise InvalidIdException("No data found for id {}".format(id_))

    def _validate_id(self, _id):
        if _id is None:
            raise InvalidIdException
        try:
            _id = int(_id)
            return self.find_by_id(_id)
        except ValueError:
            raise InvalidIdException("Incorrect ID.")

    def list_resources(self, filter=None):
        """Generator expression.

        Return a stream of items."""
        if filter is None:
            LOGGER.debug("No filter defined.")
            filter = lambda x: True
        LOGGER.debug("Resource count: %s", len(self.resources))
        for _item in self.resources:
            val = filter(_item)
            LOGGER.debug("filter value: %s", val)
            if val:
                LOGGER.debug("yielding: %s", _item.name)
                yield _item

    async def select_resource(self, default=''):
        base_prompt = BasePrompt()
        resource = self._validate_id(
            await base_prompt.current_prompt(
                "Select a {} id: ".format(self.resource_type_name),
                toolbar="Enter a {} id.".format(self.resource_type_name),
                autoreturn=True,
                autocomplete=self.id_suggestions,
                default=default,
            )
        )
        return resource

    async def get_resource(self):
        done = print_waiting_done("getting {}s".format(self.resource_type_name))
        try:

            self.resources = await self.api_entry_point.get_instances()
            self._populate_id_suggestions()
        except PvApiConnectionError as err:
            print(err)
        finally:
            await done()


class HubCache:
    """Global state of the connected hub."""

    def __init__(self, request, loop=None):
        self.shades = ResourceCache(PvShades(request), "shade", request)
        self.rooms = ResourceCache(PvRooms(request), "room", request)
        self.scenes = ResourceCache(PvScenes(request), "scene", request)
        self.scene_members = ResourceCache(
            PvSceneMembers(request), "scene member", request
        )
        self.user_data = UserData(request)
        self.loop = loop or get_loop()

    async def update(self):
        """Update the hub cache."""
        await self.shades.get_resource()
        await self.rooms.get_resource()
        await self.scenes.get_resource()
        await self.scene_members.get_resource()
        await self.user_data.update_user_data()
        await asyncio.sleep(1)
