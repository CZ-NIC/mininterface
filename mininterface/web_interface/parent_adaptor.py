import pickle
import struct
import subprocess
import sys
from typing import TYPE_CHECKING

from ..textual_interface.textual_adaptor import TextualAdaptor

if TYPE_CHECKING:
    from . import TextualInterface


class WebParentAdaptor(TextualAdaptor):

    def __init__(self, interface: "TextualInterface", environ=None, app=None):
        super().__init__(interface)
        self.process = subprocess.Popen(
            sys.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            bufsize=0,
            env=environ
        )

    def receive(self):
        """ Receives further instruction from the underlying ChildAdaptor. """
        p = self.process
        length_data = p.stdout.read(4)
        if not length_data:
            return False
        msg_length = struct.unpack("I", length_data)[0]
        received_data = p.stdout.read(msg_length)
        received_object = pickle.loads(received_data)
        form = received_object

        self.facet._fetch_from_adaptor(form)  # TODO rather use run_dialog
        return True

    def send(self, object):
        p = self.process
        serialized = pickle.dumps(object)
        p.stdin.write(struct.pack("I", len(serialized)))
        p.stdin.write(serialized)
        p.stdin.flush()

    def disconnect(self):
        try:
            self.process.stdin.write(struct.pack("I", 0))
            self.process.stdin.flush()
            self.process.wait()
        except BrokenPipeError:
            print("Child already disconnected")
