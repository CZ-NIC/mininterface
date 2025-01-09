from datetime import datetime
from pathlib import Path
from tkinter import Label
from typing import TYPE_CHECKING
from humanize import naturalsize

from ..exceptions import DependencyRequired
from ..facet import Facet, Image, LayoutElement

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

    def _layout(self, elements: list[LayoutElement]):
        try:
            from PIL import ImageTk, Image as ImagePIL
            PIL = True
        except:
            PIL = False

        for el in elements:
            match el:
                case Image():
                    if not PIL:
                        raise DependencyRequired("img")
                    filename = el.src
                    img = ImagePIL.open(filename)
                    max_width, max_height = 250, 250
                    w_o, h_o = img.size
                    scale = min(max_width / w_o, max_height / h_o)
                    img = img.resize((int(w_o * scale), int(h_o * scale)), ImagePIL.LANCZOS)
                    img_p = ImageTk.PhotoImage(img)
                    panel = Label(self.adaptor.frame, image=img_p)
                    panel.image = img_p
                    panel.pack()
                case Path():
                    size = naturalsize(el.stat().st_size)
                    mtime = datetime.fromtimestamp(el.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    Label(self.adaptor.frame, text=f"{el} / {size} / {mtime}").pack()
                case str():
                    Label(self.adaptor.frame, text=el).pack()
                case _:
                    Label(self.adaptor.frame, text=f"Error in the layout: Unknown {el}").pack()

    def submit(self, *args, **kwargs):
        super().submit(*args, **kwargs)
        self.adaptor._ok()
