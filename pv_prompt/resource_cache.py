from aiopvapi.helpers.aiorequest import AioRequest
from aiopvapi.helpers.api_base import ApiEntryPoint
from aiopvapi.rooms import Rooms as PvRooms
from aiopvapi.scene_members import SceneMembers as PvSceneMembers
from aiopvapi.scenes import Scenes as PvScenes
from aiopvapi.shades import Shades as PvShades
from prompt_toolkit.contrib.completers import WordCompleter

from pv_prompt.base_prompts import BasePrompt, InvalidIdException
from pv_prompt.helpers import coro
from pv_prompt.print_output import info, print_waiting_done


class ResourceCache:
    def __init__(self,
                 api_entry_point: ApiEntryPoint,
                 resource_type_name: str,
                 request: AioRequest):
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
        self.id_suggestions = WordCompleter(
            [str(_item.id) for _item in self.resources])

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
            raise InvalidIdException('Incorrect ID.')

    def select_resource(self):
        base_prompt = BasePrompt()
        resource = self._validate_id(
            base_prompt.current_prompt(
                "Select a {} id: ".format(self.resource_type_name),
                toolbar="Enter a {} id.".format(self.resource_type_name),
                autoreturn=True,
                autocomplete=self.id_suggestions
            )
        )
        return resource

    @coro
    async def get_resource(self):
        self.resources = await self.api_entry_point.get_instances()
        self._populate_id_suggestions()


class HubCache:
    def __init__(self, request):
        self.shades = ResourceCache(PvShades(request), 'shade', request)
        self.rooms = ResourceCache(PvRooms(request), 'room', request)
        self.scenes = ResourceCache(PvScenes(request), 'scene', request)
        self.scene_members = ResourceCache(
            PvSceneMembers(request), 'scene member', request)

    def update(self):
        done = print_waiting_done('getting shades.. ')
        self.shades.get_resource()
        done()
        done = print_waiting_done('getting rooms..')
        self.rooms.get_resource()
        done()
        self.scenes.get_resource()
        self.scene_members.get_resource()
