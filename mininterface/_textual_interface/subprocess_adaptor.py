"""Parent-side adaptor for the persistent Textual subprocess."""
import os

from ..settings import TextualSettings
from .adaptor import TextualAdaptor
from .facet import TextualFacet
from .._lib.ipc_command import IpcCommand  # noqa: F401 — kept for callers that import it from here
from .._lib.subprocess_base import SubprocessAdaptorBase

_CHILD_CMD = (
    "from mininterface._textual_interface.subprocess_child import run_child_main;"
    "run_child_main({read_fd},{write_fd})"
)


class _SubprocessFacet(TextualFacet):
    """Parent-side facet — stores raw LayoutElements instead of Textual widgets."""

    adaptor: "TextualSubprocessAdaptor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raw_layout: list = []

    def _layout(self, elements):
        self._raw_layout.extend(elements)

    def _clear(self):
        super()._clear()
        self.adaptor._clear_output()  # also empty the child's on-screen output


class TextualSubprocessAdaptor(SubprocessAdaptorBase, TextualAdaptor):
    """Parent-side adaptor. Communicates with a persistent Textual subprocess."""

    facet: _SubprocessFacet
    settings: TextualSettings
    _CHILD_CMD = _CHILD_CMD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _release_terminal_after_dialog(self) -> bool:
        # Textual owns the terminal (alternate screen + stdin) while it runs, so a
        # dialog shown outside a `with` block must let the child go afterwards or a
        # following input()/print() in the parent collides with it. Only in tty
        # mode: the web backend (TEXTUAL_DRIVER set) talks over a socket and holds
        # no local terminal, so it keeps the child persistent.
        return not os.environ.get("TEXTUAL_DRIVER")
