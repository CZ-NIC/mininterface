from enum import Enum


class TuiCommand(Enum):
    FORM = "form"
    BUTTONS = "buttons"
    SHUTDOWN = "shutdown"
    RESULT = "result"
    CANCEL = "cancel"
    CALLBACK = "callback"      # child → parent: callback fired
    FORM_UPDATE = "form_update"  # parent → child: updated tag values after callback
