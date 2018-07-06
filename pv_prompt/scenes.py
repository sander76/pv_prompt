import logging

from aiopvapi.resources.scene import Scene as PvScene
from aiopvapi.scene_members import SceneMembers

from pv_prompt.base_prompts import PvPrompt, Command, InvalidIdException, \
    PvResourcePrompt, BasePrompt
from pv_prompt.print_output import info, print_scenes, warn, \
    print_resource_data, print_table
from pv_prompt.resource_cache import HubCache

LOGGER = logging.getLogger(__name__)


class Scenes(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.scenes
        self.register_commands(
            {'l': Command(function_=self.list_scenes),
             'a': Command(function_=self.activate_scene),
             's': Command(function_=self.select_scene),
             'c': Command(function_=self.create_scene)})

    async def list_scenes(self, *args, **kwargs):
        info("Getting scenes...")
        print_scenes(self.hub_cache.scenes, self.hub_cache.rooms)

    async def activate_scene(self, *args, **kwargs):
        try:
            _scene = await self.hub_cache.scenes.select_resource()

            await _scene.activate()

        except InvalidIdException as err:
            warn(err)

    async def select_scene(self, *args, **kwargs):
        try:
            pv_scene = await self.hub_cache.scenes.select_resource()
            scene = Scene(pv_scene, self.request, self.hub_cache)
            await scene.current_prompt()
        except InvalidIdException as err:
            warn(err)

    async def create_scene(self, *args, **kwargs):
        create_scene = CreateScene(self.request, self.hub_cache)
        await create_scene.current_prompt()


class CreateScene(PvPrompt):
    def __init__(self, request, hub_cache: HubCache):
        super().__init__(request, hub_cache)
        self.api_resource = hub_cache.scenes
        self.register_commands(
            {'r': Command(function_=self.select_room),
             's': Command(function_=self.add_shade),
             'n': Command(function_=self.enter_name),
             'c': Command(function_=self.create_scene)})
        self._room = None
        self._scene_name = None

    async def print_selection(self):
        if self._room:
            print_table('room:', self._room.name, self._room.id)
        if self._scene_name:
            print_table('scene name:', self._scene_name)

    async def create_scene(self, *args, **kwargs):
        scenes_obj = self.hub_cache.scenes.api_entry_point
        await scenes_obj.create_scene(self._room.id, self._scene_name)
        await self.hub_cache.scenes.get_resource()

    async def select_room(self, *args, **kwargs):
        print_resource_data(self.hub_cache.rooms)
        try:
            self._room = await self.hub_cache.rooms.select_resource()
            await self.print_selection()
        except InvalidIdException as err:
            warn(err)

    async def enter_name(self, *args, **kwargs):
        base = BasePrompt()
        self._scene_name = await base.current_prompt(
            prompt_="Enter a scene name: ",
            autoreturn=True
        )
        await self.print_selection()

    async def add_shade(self, *args, **kwargs):
        pass


class Scene(PvResourcePrompt):
    def __init__(self, scene: PvScene, request, hub_cache):
        super().__init__(scene, request, hub_cache)
        self._prompt = 'scene {} {}:'.format(scene.id, scene.name)
        self.register_commands(
            {'a': Command(function_=self.add_shade_to_scene)})

    async def add_shade_to_scene(self, *args, **kwargs):
        shade = await self.hub_cache.shades.select_resource()
        _position = await shade.get_current_position()
        if _position:
            await (SceneMembers(self.request)).create_scene_member(
                _position, self.api_resource.id, shade.id)
        info('Scene created.')

    async def show_members(self, *args, **kwargs):
        info("getting scene members")
        _scene_members = self.hub_cache.scene_members.re
