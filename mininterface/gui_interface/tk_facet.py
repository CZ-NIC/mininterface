from typing import TYPE_CHECKING
from ..facet import Facet

if TYPE_CHECKING:
    from .tk_window import TkWindow


class TkFacet(Facet):
    window: "TkWindow"

    def set_title(self, title: str):
        if not title:
            self.window.label.pack_forget()
        else:
            self.window.label.config(text=title)
            self.window.label.pack(pady=10)
            pass

    def submit(self):
        self.window.form.button.invoke()
