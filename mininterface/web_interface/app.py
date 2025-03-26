from typing import TYPE_CHECKING

from ..textual_interface.textual_app import TextualApp

if TYPE_CHECKING:
    from .parent_adaptor import WebParentAdaptor


class WebParentApp(TextualApp):
    adaptor: "WebParentAdaptor"

    def on_mount(self):
        if self.adaptor.receive():
            super().on_mount()
        else:
            self.exit()

    def action_confirm(self):
        self.adaptor.send(self.adaptor.facet._form)
        self.on_mount()

    def action_exit(self):
        self.exit()
        # TODO rather raise cancelled?
