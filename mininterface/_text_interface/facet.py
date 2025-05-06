from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .._lib.auxiliary import naturalsize  # light-weight humanize clone
from ..facet import Facet, Image, LayoutElement

if TYPE_CHECKING:
    from .adaptor import TextAdaptor


class TextFacet(Facet):
    adaptor: "TextAdaptor"

    def set_title(self, title: str):
        print(">>>", title, "<<<")

    def _layout(self, elements: list[LayoutElement]):
        for el in elements:
            match el:
                case Image():
                    print("Image:", el.src)
                case Path():
                    size = naturalsize(el.stat().st_size)
                    mtime = datetime.fromtimestamp(el.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{el} / {size} / {mtime}")
                case str():
                    print(el)
                case _:
                    print("Error in the layout: Unknown {el}")
