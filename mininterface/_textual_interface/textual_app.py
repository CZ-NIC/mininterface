from typing import TYPE_CHECKING
from textual import events
from textual.app import App
from textual.containers import Container
from textual.widget import Widget

from .form_contents import FormContents

from .button_contents import ButtonContents


from .widgets import TagWidget


if TYPE_CHECKING:
    from .adaptor import TextualAdaptor

WidgetList = list[Widget | TagWidget]


class TextualApp(App[bool | None]):
    # BINDINGS = [ These are being ignored in the input fields, hence we use on_key
    #     ("up", "go_up", "Go up"),
    #     ("down", "go_up", "Go down"),
    # ]

    # We need to jump out of dir to allow children inherits (WebInterface)
    CSS_PATH = "../_textual_interface/style.tcss"

    def __init__(self, adaptor: "TextualAdaptor", submit: str | bool = True):
        super().__init__()
        self.widgets: WidgetList = []
        self.focusable_: WidgetList = []
        self.adaptor = adaptor
        self.submit = submit

        # Form confirmation
        if submit:
            # enter w/o priority is still consumed by input fields (and recaught by on_key)
            # Second thing:
            # I know "Enter" is not a valid shortcut.
            # But having writter 'enter' would mean it would be not shown in Input field.
            # And I do want to send the form on enter.
            # So the shortcut does not work but is handled at 'on_key'.
            self.bind("Enter", "confirm", description=submit if isinstance(submit, str) else "Ok")
        self.bind("escape", "exit", description="Cancel")

    def compose(self):
        self.contents = Container()
        yield self.contents

    def on_mount(self) -> None:
        self.has_been_confirmed = False
        # def on_mount(self, event: events.Mount) -> None:
        self.contents.remove_children()
        if self.adaptor.button_app:
            c = ButtonContents(self.adaptor, self.adaptor.button_app)
        else:
            c = FormContents(self.adaptor, self.widgets, self.focusable_)
        self.contents.mount(c)

    def action_confirm(self):
        # next time, start on the same widget
        # NOTE the functionality is probably not used
        self.focused_i = next((i for i, inp in enumerate(self.focusable_) if inp == self.focused), None)
        self.exit(True)

    def action_exit(self):
        self.exit()
