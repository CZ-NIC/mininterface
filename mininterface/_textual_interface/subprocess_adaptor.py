"""Parent-side adaptor for the persistent Textual subprocess."""
from ..settings import TextualSettings
from .adaptor import TextualAdaptor
from .facet import TextualFacet
from .tui_command import TuiCommand  # noqa: F401 — kept for callers that import it from here
from .._lib.subprocess_base import SubprocessAdaptorBase

_CHILD_CMD = (
    "from mininterface._textual_interface.subprocess_child import run_child_main;"
    "run_child_main({read_fd},{write_fd})"
)


class _SubprocessFacet(TextualFacet):
    """Parent-side facet — stores raw LayoutElements instead of Textual widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raw_layout: list = []

    def _layout(self, elements):
        self._raw_layout.extend(elements)


class TextualSubprocessAdaptor(SubprocessAdaptorBase, TextualAdaptor):
    """Parent-side adaptor. Communicates with a persistent Textual subprocess."""

    facet: _SubprocessFacet
    settings: TextualSettings
    _CHILD_CMD = _CHILD_CMD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
