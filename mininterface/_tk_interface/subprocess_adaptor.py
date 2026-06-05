"""Parent-side adaptor for the persistent Tk subprocess.

Independent of Tk (variant B): the parent never imports tkinter nor builds
widgets — it only ships forms over the pipe and lets the child render them.
Widgetisation, layout rendering and submit handling all happen in the child.
"""
from ..facet import Facet
from ..settings import GuiSettings
from ..tag import Tag
from .._lib.subprocess_base import SubprocessAdaptorBase

_CHILD_CMD = (
    "from mininterface._tk_interface.subprocess_child import run_child_main;"
    "run_child_main({read_fd},{write_fd})"
)


class _SubprocessTkFacet(Facet):
    """Parent-side facet — no Tk.

    Records the title and raw layout elements so the IPC layer can ship them to
    the child, where the real TkFacet renders them.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._title = ""
        self._raw_layout: list = []

    def set_title(self, title: str):
        self._title = title

    def _layout(self, elements):
        self._raw_layout.extend(elements)

    # submit() is inherited from Facet — it only records post_submit_action,
    # which the IPC callback channel turns into a CALLBACK("button").


class TkSubprocessAdaptor(SubprocessAdaptorBase):
    """Parent-side adaptor. Communicates with a persistent Tk subprocess."""

    facet: _SubprocessTkFacet
    settings: GuiSettings
    _CHILD_CMD = _CHILD_CMD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The parent never builds widgets, so it would not notice a missing
        # display. Probe it here (cheap, tkinter only) so get_interface can fall
        # back to a TUI on headless systems, just like the in-process adaptor did.
        self._check_display()
        # Start loading the Tk child process as early as possible (when the
        # interface is created, typically at run()) so its import cost is hidden
        # behind the user code that runs before the first .form call.
        self._ensure_process()

    @staticmethod
    def _check_display():
        """Raises: InterfaceNotAvailable if no usable display is present."""
        import tkinter

        try:
            root = tkinter.Tk()
        except tkinter.TclError:
            from ..exceptions import InterfaceNotAvailable

            raise InterfaceNotAvailable
        root.destroy()

    def _get_redirected(self) -> str:
        """Drain the parent's pending stdout buffer into the next dialog's header."""
        try:
            return self.interface._redirected.join()
        except AttributeError:
            return ""

    def widgetize(self, tag: Tag):
        # Widgetisation happens in the child; the parent never builds widgets.
        pass

    def yes_no(self, text: str, focus_no=True, *, timeout: int = 0):
        return self.buttons(text, [("Yes", True), ("No", False)], int(focus_no) + 1, timeout=timeout)
