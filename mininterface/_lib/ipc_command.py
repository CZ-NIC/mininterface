from enum import Enum


class IpcCommand(Enum):
    """Message kinds exchanged over the parent⇄child pipe of every subprocess
    UI backend — both the Tk GUI and the Textual TUI use the same protocol."""

    FORM = "form"
    BUTTONS = "buttons"
    SHUTDOWN = "shutdown"
    RESULT = "result"
    CANCEL = "cancel"
    QUIT = "quit"                # child → parent: window closed (X) → exit the program
    ERROR = "error"              # child → parent: dialog build crashed (exception + traceback text)
    CALLBACK = "callback"        # child → parent: callback fired
    FORM_UPDATE = "form_update"   # parent → child: updated tag values after callback
    VALIDATE_RESULT = "validate_result"  # parent → child: result of a live validation round-trip
    OUTPUT = "output"            # parent → child: live print() text to stream
    CLEAR_OUTPUT = "clear_output"  # parent → child: clear the streamed-output widget
    SETTINGS = "settings"        # parent → child: the UI settings (sent once after spawn)
