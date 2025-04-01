import pickle
import struct
import subprocess
import sys
from typing import TYPE_CHECKING

from ..auxiliary import flatten

from ..textual_interface.facet import TextualFacet

from ..options import WebOptions

from ..facet import Facet

from ..textual_interface.adaptor import TextualAdaptor

if TYPE_CHECKING:
    from . import TextualInterface


class WebParentAdaptor(TextualAdaptor):

    facet: TextualFacet  # NOTE proper facet
    options: WebOptions

    def __init__(self, *args, environ=None, app=None):
        super().__init__(*args)
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
        # TODO this reads form only, we should be able to read ex. print output
        received_data = p.stdout.read(msg_length)
        received_object = pickle.loads(received_data)
        form = received_object

        # sets the facet to all the tags in the form
        for t in flatten(received_object):
            t.facet = self.facet

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
