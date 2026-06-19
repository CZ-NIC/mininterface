import builtins
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self, Type
else:
    from typing import Type


class RedirectText:
    """Helps to redirect text from stdout to a text widget."""

    def __init__(self) -> None:
        self.max_lines = 1000
        self.pending_buffer = []
        self.output_callback = None
        self._line_buffer = ""
        self.streamed_buffer = []
        """ Lines handed to output_callback (i.e. sent over IPC to the child) that the
            child has not yet confirmed it rendered. A new dialog re-renders this whole
            output area, so the adaptor clears this each time it sends one. Whatever
            remains when the `with` block exits is the tail the child never managed to
            show (e.g. a print() as the last statement of the block) — __exit__ replays
            it to the real stdout so it is not lost. """

    def write(self, text):
        if self.output_callback:
            self._line_buffer += text
            while "\n" in self._line_buffer:
                line, self._line_buffer = self._line_buffer.split("\n", 1)
                self.streamed_buffer.append(line)
                self.output_callback(line)
        else:
            self.pending_buffer.append(text)

    def flush(self):
        pass  # required by sys.stdout

    def join(self):
        t = "".join(self.pending_buffer)
        self.clear()
        return t

    def isatty(self):  # required by an interface
        return False

    def clear(self):
        self.pending_buffer.clear()

    def confirm_streamed(self):
        """Mark everything streamed so far as rendered by the child. Called by the
        adaptor right before it sends a new dialog (which re-renders the whole output
        area), so streamed_buffer only ever holds the not-yet-shown tail."""
        self.streamed_buffer.clear()


class Redirectable:
    """When enwraped in a with statement, the prints go to the UI instead of a stdout."""

    # NOTE When used in the with statement, the TUI window should not vanish between dialogs.
    # The same way the GUI does not vanish.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._always_shown = False
        self._redirected: RedirectText = RedirectText()
        self._original_stdout = sys.stdout

    def __enter__(self) -> "Self":
        self._always_shown = True
        sys.stdout = self._redirected
        # The subprocess child owns the tty for the whole `with` block, so reading
        # it directly would fight the child for stdin (Textual hangs) or pop an
        # invisible prompt into a stray window (Tk). Route the stdlib prompts
        # through the same UI as the redirected stdout — a dialog, like m.ask().
        self._original_input = builtins.input
        builtins.input = self._redirected_input
        # Patch getpass only if the program already imported it — never import it
        # ourselves, so startup cost stays untouched when getpass is unused.
        self._getpass = sys.modules.get("getpass")
        if self._getpass is not None:
            self._original_getpass = self._getpass.getpass
            self._getpass.getpass = self._redirected_getpass  # type: ignore[attr-defined]
        return self

    def _redirected_input(self, prompt="") -> str:
        """input() replacement active inside the `with` block (see __enter__).

        Mirrors the built-in: the prompt becomes the field label, a string is
        returned, and a cancelled dialog raises EOFError (as input() does on EOF)."""
        from ..exceptions import Cancelled
        try:
            return self.ask(str(prompt))  # type: ignore[attr-defined]
        except Cancelled:
            raise EOFError

    def _redirected_getpass(self, prompt="Password: ", stream=None) -> str:
        """getpass.getpass() replacement active inside the `with` block.

        getpass reads /dev/tty directly (bypassing the stdout redirect), so route
        it to a masked dialog instead. `stream` is accepted for signature
        compatibility and ignored. A cancelled dialog raises EOFError, matching
        getpass on EOF."""
        from ..exceptions import Cancelled
        from ..tag import SecretTag
        try:
            return self.ask(str(prompt), SecretTag)  # type: ignore[attr-defined]
        except Cancelled:
            raise EOFError

    def __exit__(self, *_):
        self._always_shown = False
        sys.stdout = self._original_stdout
        builtins.input = self._original_input
        if self._getpass is not None:
            self._getpass.getpass = self._original_getpass  # type: ignore[attr-defined]

        # Parent and child share the tty. Bring the child UI fully down first so it
        # restores the terminal (leaves the alternate screen, raw mode, hidden
        # cursor) before we write any plain text below — otherwise the reprint and
        # the script's post-`with` output land in the child's screen and corrupt the
        # terminal. No-op for in-process / non-subprocess interfaces.
        adaptor = getattr(self, "_adaptor", None)
        if adaptor is not None and hasattr(adaptor, "_shutdown_ui"):
            try:
                adaptor._shutdown_ui()
            except Exception:
                pass

        # Text printed via the non-IPC path (no live child) was buffered; flush it.
        if t := self._redirected.join():  # display text sent to the window but not displayed
            print(t, end="")

        # Text streamed to the child that it never managed to render (typically a
        # print() as the last statement of the `with` block: it reaches the closing
        # child over IPC but no further dialog re-renders the output area). Replay it
        # to the real stdout so it is not silently swallowed.
        r = self._redirected
        tail = list(r.streamed_buffer)
        if r._line_buffer:  # an unterminated final line never handed to output_callback
            tail.append(r._line_buffer)
            r._line_buffer = ""
        r.streamed_buffer.clear()
        if tail:
            print("\n".join(tail))
