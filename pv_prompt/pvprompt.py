import asyncio

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout

buffer1 = Buffer()  # Editable buffer.

root_container = VSplit(
    [
        # One window that holds the BufferControl with the default buffer on
        # the left.
        HSplit(

        ),
        # A vertical line in the middle. We explicitly specify the width, to
        # make sure that the layout engine will not try to divide the whole
        # width by three for all these windows. The window will simply fill its
        # content by repeating this character.
        Window(width=1, char="|"),
        # Display the text 'Hello world' on the right.
        Window(content=FormattedTextControl(text="Hello world")),
    ]
)

layout = Layout(root_container)

app = Application(layout=layout, full_screen=True)


def main():
    use_asyncio_event_loop()

    asyncio.get_event_loop().run_until_complete(
        app.run_async().to_asyncio_future()
    )


if __name__ == "__main__":
    main()
