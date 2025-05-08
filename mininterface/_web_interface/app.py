from enum import Enum
from typing import TYPE_CHECKING

from .._textual_interface.textual_app import TextualApp

if TYPE_CHECKING:
    from .parent_adaptor import WebParentAdaptor


class SerCommand(Enum):
    FORM = "form"
    BUTTONS = "buttons"


def w(*text):
    from pathlib import Path
    f = Path("/tmp/ram/log").open("a")
    f.write(" ".join(str(s) for s in text) + "\n")
    f.close()


class WebParentApp(TextualApp):
    adaptor: "WebParentAdaptor"

    def on_mount(self, first_call: bool = False):
        if self.adaptor.receive():
            if not first_call:
                # on the first call, Textual parent is called automatically
                super().on_mount()
        else:
            self.exit()

    def action_confirm(self):
        if self.adaptor.button_app:
            self.adaptor.send(self.adaptor._get_buttons_val())
        else:
            self.adaptor.send(self.adaptor._serialize_vals(self.app))
        self.on_mount(first_call=False)

    def action_exit(self):
        self.exit()
        # NOTE rather raise cancelled?
