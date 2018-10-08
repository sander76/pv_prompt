import asyncio

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, BufferControl, to_container
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import Button


class MainMenu:
    def __init__(self, loop):
        self.loop = loop
        self.log_output = Buffer()
        self.root_container = VSplit(
            [
                Context(loop, self.log_output).buttons,
                Window(width=1, char="|"),
                Window(BufferControl(buffer=self.log_output)),
            ]
        )

        self.app = Application(
            Layout(self.root_container),
            full_screen=True,
            key_bindings=self.get_bindings(),
        )

    def change_context(self):
        other = OtherContext(self.loop, self.log_output)
        self.root_container.key_bindings=other.get_key_bindings()
        self.root_container.children[0] = other.buttons


    def get_bindings(self):
        kb = KeyBindings()

        @kb.add("c-q")
        def _(event):
            print("exiting")
            event.app.exit()

        @kb.add("c-c")
        def _(event):
            self.change_context()

        return kb


class Context:
    def __init__(self, loop, logbuffer):
        self._buttons = HSplit(
            [Button("command_1", handler=self.command_1)],
            key_bindings=self.get_key_bindings(),
        )

        self.loop = loop
        self.logbuffer = logbuffer

    @property
    def buttons(self):
        return self._buttons

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add("c-s")
        def _(event):
            self.command_1()

        return kb

    def command_1(self):
        self.logbuffer.text = self.logbuffer.text + "\ncommand_1"


class OtherContext:
    def __init__(self, loop, logbuffer):
        self._buttons = HSplit(
            [Button("command_2", handler=self.command_2)],
            key_bindings=self.get_key_bindings(),
        )

        self.loop = loop
        self.logbuffer = logbuffer

    @property
    def buttons(self):
        return self._buttons

    def get_key_bindings(self):
        kb = KeyBindings()

        @kb.add("c-o")
        def _(event):
            print("other")
            self.command_2()

        return kb

    def command_2(self):
        self.logbuffer.text = self.logbuffer.text + "\ncommand_2"


def main():
    use_asyncio_event_loop()
    loop = asyncio.get_event_loop()
    main_menu = MainMenu(loop)

    loop.run_until_complete(main_menu.app.run_async().to_asyncio_future())


if __name__ == "__main__":
    main()
