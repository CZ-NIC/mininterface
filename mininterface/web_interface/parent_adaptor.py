import logging
import pickle
import struct
import subprocess
import sys
from types import GeneratorType
from typing import TYPE_CHECKING


from ..form_dict import TagDict

from .app import SerCommand, WebParentApp

from ..auxiliary import flatten

from ..textual_interface.facet import TextualFacet

from ..options import WebOptions

from ..facet import Facet

from ..textual_interface.adaptor import TextualAdaptor
from ..textual_interface.button_contents import ButtonAppType

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
        self.app = app = WebParentApp(self, submit=True)
        app.run()

    def receive(self):
        """ Receives further instruction from the underlying ChildAdaptor. """
        p = self.process
        length_data = p.stdout.read(4)
        if not length_data:
            return False
        msg_length = struct.unpack("I", length_data)[0]
        command, text, data = pickle.loads(p.stdout.read(msg_length))

        self.interface._redirected.write(text)
        match command, data:
            case SerCommand.FORM, [form]:
                form: TagDict

                # sets the facet to all the tags in the form
                for t in flatten(form):
                    t.facet = self.facet

                self.button_app = False
                self.facet._fetch_from_adaptor(form)  # TODO rather use run_dialog
            case SerCommand.BUTTONS, data:
                data: ButtonAppType
                self._build_buttons(*data)
            case _:
                raise ValueError("Web parent: Unknown command from child")
        return True

    def send(self, object):
        p = self.process
        if isinstance(object, GeneratorType):
            object = list(object)
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
