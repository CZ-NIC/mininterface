from typing import TYPE_CHECKING
from ..facet import Facet

if TYPE_CHECKING:
    from .tk_window import TkWindow


class TkFacet(Facet):
    adaptor: "TkWindow"

    def set_title(self, title: str):
        if not title:
            self.adaptor.label.pack_forget()
        else:
            self.adaptor.label.config(text=title)
            self.adaptor.label.pack(pady=10)
            pass

    def submit(self, *args, **kwargs):
        super().submit(*args, **kwargs)
        self.adaptor._ok()
