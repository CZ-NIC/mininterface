from datetime import datetime
from typing import TYPE_CHECKING

from pathlib import Path

from textual.widgets import Label

from humanize import naturalsize

from ..exceptions import DependencyRequired
from ..facet import Facet, Image, LayoutElement

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor


class TextualFacet(Facet):
    adaptor: "TextualAdaptor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Since TextualApp turns off, we need to have its values stored somewhere
        self._title = ""

    # NOTE: multiline title will not show up
    def set_title(self, title: str):
        self._title = title
        if self.adaptor.app is not None:
            self.adaptor.app.title = title

    def _layout(self, elements: list[LayoutElement]):
        append = self.adaptor.layout_elements.append
        try:
            from PIL import Image as ImagePIL
            from textual_imageview.viewer import ImageViewer

            PIL = True
        except:
            PIL = False

        for el in elements:
            match el:
                case Image():
                    if not PIL:
                        raise DependencyRequired("img")
                    append(ImageViewer(ImagePIL.open(el.src)))
                case Path():
                    size = naturalsize(el.stat().st_size)
                    mtime = datetime.fromtimestamp(el.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    append(Label(f"{el} / {size} / {mtime}", markup=False))
                case str():
                    append(Label(el, markup=False))
                case _:
                    append(Label("Error in the layout: Unknown {el}", markup=False))

    def submit(self, *args, **kwargs):
        super().submit(*args, **kwargs)
        # When you receive Facet in Command.init, the app does not exist yet
        if self.adaptor.app is not None:
            self.adaptor.app.action_confirm()
