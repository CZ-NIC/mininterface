from typing import TYPE_CHECKING
from ..facet import Facet
if TYPE_CHECKING:
    from .textual_app import TextualApp


class TextualFacet(Facet):
    def __init__(self, window: "TextualApp"):
        self.window = window
        # Since TextualApp turns off, we need to have its values stored somewhere
        self._title = ""

    def set_title(self, title: str):
        self._title = title
        self.window.title = title

    def submit(self):
        self.window.action_confirm()
