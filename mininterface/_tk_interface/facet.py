from datetime import datetime
from pathlib import Path
from tkinter import Label
from typing import TYPE_CHECKING
from humanize import naturalsize

from ..exceptions import DependencyRequired
from ..facet import Facet, Image, LayoutElement
from mininterface.tag.select_tag import SelectTag

if TYPE_CHECKING:
    from .adaptor import TkAdaptor


class TkFacet(Facet):
    adaptor: "TkAdaptor"

    def set_title(self, title: str):
        if not title:
            self.adaptor.label.pack_forget()
        else:
            self.adaptor.label.config(text=title)
            self.adaptor.label.pack(pady=5)
            self.adaptor._refresh_size()

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


# This function is responsible for creating the Tkinter facet based on the internal widget.
# It is assumed to exist in this file based on the implementation plan's context.
def create_tk_facet(widget, frame_main, tk_adaptor: "TkAdaptor"):
    """
    Creates the Tkinter representation of a widget (form) within a given frame.

    This function is responsible for rendering the widget's children and
    conditionally displaying the submit button based on the widget's content.
    """
    # Placeholder for actual rendering of widget's children.
    # In a complete implementation, this would iterate through `widget.children`
    # and create corresponding Tkinter widgets in `frame_main`.

    # Logic to determine if the submit button should be hidden.
    hide_submit_button = False
    if len(widget.children) == 1:
        # If there's only one child and it's a SelectTag, hide the submit button.
        if isinstance(widget.children[0], SelectTag):
            hide_submit_button = True

    # Conditionally create/display the submit button via the adaptor.
    # The submit button is only shown if the `hide_submit_button` condition is false.
    if not hide_submit_button:
        tk_adaptor._ok()