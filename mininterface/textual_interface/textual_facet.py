from typing import TYPE_CHECKING
from ..facet import Facet
if TYPE_CHECKING:
    from .textual_adaptor import TextualAdaptor


class TextualFacet(Facet):
    adaptor: "TextualAdaptor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Since TextualApp turns off, we need to have its values stored somewhere
        self._title = ""

    # NOTE: multiline title will not show up
    def set_title(self, title: str):
        self._title = title
        self.adaptor.app.title = title

    def submit(self, *args, **kwargs):
        super().submit(*args, **kwargs)
        self.adaptor.app.action_confirm()
