
from io import BytesIO, StringIO, TextIOWrapper
import pickle
import struct
import sys
from typing import TYPE_CHECKING

from textual.widget import Widget

from ..auxiliary import flatten

from ..textual_interface import TextualAdaptor

from ..textual_interface.adaptor import ButtonAppType, ValsType

from .app import SerCommand

from ..facet import Facet
from ..form_dict import TagDict
from ..mininterface.adaptor import BackendAdaptor
from ..options import WebOptions
from ..tag import Tag
from ..textual_interface.facet import TextualFacet
from ..textual_interface.widgets import TagWidget

if TYPE_CHECKING:
    from ..mininterface import Mininterface


class SerializedChildAdaptor(TextualAdaptor):
    """ Serialized output, piped to the parent process. """

    facet: TextualFacet  # TODO?
    options: WebOptions

    def __init__(self, interface: "Mininterface", options):
        super().__init__(interface, options)
        self._original_stdout = sys.stdout
        self._redirected = sys.stdout = TextIOWrapper(BytesIO())

    def receive(self):
        length_data = sys.stdin.buffer.read(4)
        if not length_data:
            sys.stdout = self._original_stdout
            print("Child process exiting now", file=sys.stderr, flush=True)
            quit()

        msg_length = struct.unpack("I", length_data)[0]
        if msg_length == 0:
            sys.stdout = self._original_stdout
            print("Child process exiting.", file=sys.stderr, flush=True)
            quit()

        serialized_data = sys.stdin.buffer.read(msg_length)
        # sys.stderr.write("Child: Debug" + str(serialized_data))
        msg = pickle.loads(serialized_data)
        return msg

    def send(self, command: SerCommand, *msg):
        self._redirected.flush()
        printed = self._redirected.buffer.getvalue().decode()
        response_data = pickle.dumps((command, printed, msg))
        self._redirected.buffer.truncate(0)
        self._redirected.buffer.seek(0)
        self._original_stdout.buffer.write(struct.pack("I", len(response_data)))
        self._original_stdout.buffer.write(response_data)
        self._original_stdout.buffer.flush()
        return self.receive()

    def widgetize(self, tag: Tag) -> Widget | TagWidget:
        """ Wrap Tag to a textual widget. """
        return  # TODO. Why does this work.

    def header(self, text: str):
        """ Generates a section header """
        return  # TODO

    def buttons(self, text: str, buttons: ButtonAppType, focused: int = 1):
        return self.send(SerCommand.BUTTONS, text, buttons, focused)

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        BackendAdaptor.run_dialog(self, form, title, submit)
        vals: ValsType = self.send(SerCommand.FORM, self.facet._form)

        if not self._try_submit((orig_tag, ui_val) for orig_tag, (_, ui_val) in zip(flatten(self.facet._form), vals)):
            return self.run_dialog(form, title, submit)

        return self.facet._form
