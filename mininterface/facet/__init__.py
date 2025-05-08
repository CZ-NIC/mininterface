from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Generic, Optional, TypeVar
from warnings import warn


from .._lib.redirectable import Redirectable


from .._lib.form_dict import EnvClass, TagDict

if TYPE_CHECKING:
    from .._mininterface.adaptor import BackendAdaptor
    from typing import Self  # remove the line as of Python3.11 and make `"Self" -> Self`


@dataclass
class Image:
    """ NOTE. Experimental. """

    src: str | Path
    """ Src to the image. """


LayoutElement = TypeVar("LayoutElement", str, Image, Path, "Self")
""" Either a string, Path or facet.Image. """


class Facet(Generic[EnvClass]):
    """ A frontend side of the interface. While a dialog is open,
        this allows to set frontend properties like the heading.

    Read [`Tag.facet`][mininterface.Tag.facet] to see how to access it from the front-end side.
    Read [`Mininterface.facet`][mininterface.Mininterface.facet] to see how to access it from the back-end side.
    """
    # Every UI adopts this object through BackendAdaptor methods.

    _form: TagDict | None = None
    """ Experimental (apparently read-only) access to the current form. """
    _env: EnvClass | None = None
    """ Experimental access to the Mininterface.env.
    If you change something, it will not probably be shown in the form because there is no refresh mechanism.
    """

    def __init__(self, adaptor: "BackendAdaptor", env: EnvClass):
        self.adaptor = adaptor
        self._env = env

    def _fetch_from_adaptor(self, form: TagDict):
        self._form = form

    def _clear(self):
        """ Experimental.
        Clear redirected text. """
        if isinstance(self.adaptor.interface, Redirectable):
            self.adaptor.interface._redirected.clear()

    def set_title(self, text):
        """ Set the main heading. """
        print("Title", text)

    def _layout(self, elements: list[LayoutElement]):
        """ Experimental. Input is a list of `LayoutElements`."""
        # NOTE remove warn when working in textual
        warn("Facet layout not implemented for this interface.")

    def submit(self, _post_submit=None):
        """ Submits the whole form.

        ```python
        from mininterface import run, Tag

        def callback(tag: Tag):
            tag.facet.submit()

        m = run()
        out = m.form({
            "My choice": Tag(options=["one", "two"], on_change=callback)
        })
        # continue here immediately after clicking on a radio button
        ```

        """
        self.adaptor.post_submit_action = _post_submit

    # NOTE we should get
    # Access to the fields. What is a catch,
    # if we change a value in the UI, their respective tag val is unchanged. Do we publish Tag values or UI values?
    # We would like to be able to refresh the Widget when update fails. However, facet does not allow method for that yet.
