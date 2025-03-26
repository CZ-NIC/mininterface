
import pickle
import struct
import subprocess
import sys
from typing import TYPE_CHECKING


from textual.widget import Widget
from textual.widgets import Rule, Label, RadioButton


from ..textual_interface.textual_adaptor import TextualAdaptor
from ..textual_interface.textual_facet import TextualFacet

from ..auxiliary import flatten
from ..exceptions import Cancelled
from ..experimental import SubmitButton
from ..facet import BackendAdaptor, Facet
from ..form_dict import TagDict, formdict_to_widgetdict
from ..tag import Tag
from ..types import DatetimeTag, PathTag, SecretTag
from ..textual_interface.textual_app import TextualApp, WidgetList
from ..textual_interface.widgets import (Changeable, MyButton, MyCheckbox, MyInput, MyRadioSet,
                                         MySubmitButton, SecretInput)

if TYPE_CHECKING:
    from ..mininterface import Mininterface
    from . import TextualInterface
    from .app import WebParentApp


class SerializedChildAdaptor(BackendAdaptor):
    """ Serialized output, piped to the parent process. """

    def __init__(self, interface: "Mininterface"):
        self.facet = Facet(self, interface.env)  # TODO, proper Facet
        pass

    def receive(self):
        length_data = sys.stdin.buffer.read(4)
        if not length_data:
            print("Child process exiting now", file=sys.stderr, flush=True)
            quit()

        msg_length = struct.unpack("I", length_data)[0]
        if msg_length == 0:
            print("Child process exiting.", file=sys.stderr, flush=True)
            quit()

        serialized_data = sys.stdin.buffer.read(msg_length)
        # sys.stderr.write("Child: Debug" + str(serialized_data))
        msg = pickle.loads(serialized_data)
        return msg

    def send(self, msg):
        response_data = pickle.dumps(msg)
        sys.stdout.buffer.write(struct.pack("I", len(response_data)))  # Poslat délku zprávy
        sys.stdout.buffer.write(response_data)
        sys.stdout.buffer.flush()
        return self.receive()

    def widgetize(self, tag: Tag) -> Widget | Changeable:
        """ Wrap Tag to a textual widget. """
        return  # TODO. Why does this work.

    def header(self, text: str):
        """ Generates a section header """
        return  # TODO

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        super().run_dialog(form, title, submit)
        return self.send(self.facet._form)
