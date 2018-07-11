import asyncio

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, BufferControl
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Button

logbuffer = Buffer()

kb = KeyBindings()


@kb.add("c-q")
def _(event):
    print("exiting")
    event.app.exit()


class MainMenu:
    def __init__(self, loop):
        self.loop = loop

        self.log_output = Buffer()
        self.context = Context(loop, self.log_output)
        self.button_container = HSplit(children=self.context.buttons)
        self.root_container = VSplit(
            [
                self.button_container,
                Window(width=1, char="|"),
                Window(BufferControl(buffer=self.log_output)),
            ]
        )

        self.app = Application(
            Layout(self.root_container), full_screen=True, key_bindings=kb
        )


class Context:
    def __init__(self, loop, logbuffer):
        self.loop = loop
        self.logbuffer = logbuffer
        self._buttons = [Button("settings", handler=self.settings)]

    @property
    def buttons(self):
        return self._buttons

    def settings(self):
        print("test")
        self.logbuffer.text = "settings"


# button_container = HSplit(children=Context().buttons)

# root_container = VSplit(
#     [
#         # One window that holds the BufferControl with the default buffer on
#         # the left.
#         button_container,
#         # A vertical line in the middle. We explicitly specify the width, to
#         # make sure that the layout engine will not try to divide the whole
#         # width by three for all these windows. The window will simply fill its
#         # content by repeating this character.
#         Window(width=1, char="|"),
#         Window(BufferControl(buffer=logbuffer)),
#     ]
# )
#
# layout = Layout(root_container)
#
# app = Application(layout=layout, full_screen=True)


class MainContext(Context):
    async def another(self):
        print()


def main():
    use_asyncio_event_loop()
    loop = asyncio.get_event_loop()
    main_menu = MainMenu(loop)

    loop.run_until_complete(main_menu.app.run_async().to_asyncio_future())
    # asyncio.get_event_loop().run_until_complete(
    #     app.run_async().to_asyncio_future()
    # )


if __name__ == "__main__":
    main()
