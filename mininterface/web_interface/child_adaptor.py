
import pickle
import struct
import sys
from typing import TYPE_CHECKING

from textual.widget import Widget

from ..textual_interface.facet import TextualFacet

from ..options import WebOptions

from ..form_dict import TagDict
from ..mininterface.adaptor import BackendAdaptor
from ..facet import Facet
from ..tag import Tag
from ..textual_interface.widgets import Changeable

if TYPE_CHECKING:
    from ..mininterface import Mininterface


class SerializedChildAdaptor(BackendAdaptor):
    """ Serialized output, piped to the parent process. """

    facet: TextualFacet  # TODO?
    options: WebOptions

    def __init__(self, interface: "Mininterface", options):
        # self.facet = Facet(self, interface.env)  # TODO, proper Facet
        super().__init__(interface, options)
        self.layout_elements = []  # TODO
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
        sys.stdout.buffer.write(struct.pack("I", len(response_data)))
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
