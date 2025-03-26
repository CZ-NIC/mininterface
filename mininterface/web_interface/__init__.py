""" Raises InterfaceNotAvailable at module import time if textual not installed or session is non-interactive. """
import os
import sys
from typing import Optional

from ..textual_interface import TextualInterface
from .child_adaptor import SerializedChildAdaptor
from .parent_adaptor import WebParentAdaptor

try:
    from textual.app import App as _ImportCheck
except ImportError:
    from ..exceptions import InterfaceNotAvailable
    raise InterfaceNotAvailable

from ..exceptions import DependencyRequired, InterfaceNotAvailable
from .app import WebParentApp


class WebInterface(TextualInterface):

    def __init__(self, *args, cmd: Optional[str] = None, port=64646, **kwargs):
        super().__init__(*args, need_atty=False, **kwargs)
        # TODO
        # * Yes/no/alert support (ButtonApp).
        # * lambda, print, on_change, layout, SubmitTrue support
        # * ex. validation does not work
        # * Docs image.
        # * Port should be set from a config file too.

        # This is a nifty solution.
        # Common use of textual application is that everything is wrapped inside, the textual library is used
        # as a framework. That way, it would be impossible to easily switch to another interface. Instead,
        # we invoke another textual app per form.
        # However, textual-serve uses only the first textual application. So we cannot use bare textual app
        # as it would end after the first form submit.
        #   with run(interface=WebInterface) as m:
        #     m.form({"hello": 1})  # the app ends here
        #     m.form({"hello": 2})  # we never get here
        # We handle it this way: The textual-serve re-runs the program to get the textual app
        # in an underlying process '_web-parent'.
        # From there, we re-run the program once more. The textual app fetches the commands from there.
        # Running the program thrice was the only solution I came up with.
        #
        # Why not doing that for every TextualApp? If invoking the interface would not be the first thing
        # the program does, lines before get launched multiple times.
        #
        #   hello = "world"  # This line would run twice for TextualInterface
        #   with run(interface=TextualInterface) as m:
        #     m.form({"hello": 1})  # the app ends here
        #     m.form({"hello": 2})  # we never get here
        match os.environ.get("MININTERFACE_ENFORCED_WEB"):
            case '_web-child-serialized':
                self.adaptor = SerializedChildAdaptor(self)
                return
            case '_web-parent':
                envir = os.environ.copy()
                envir["MININTERFACE_ENFORCED_WEB"] = '_web-child-serialized'
                self.adaptor = WebParentAdaptor(self, environ=envir)
                self.adaptor.app = self.app = app = WebParentApp(self.adaptor, submit=True)
                app.run()
                self.adaptor.disconnect()
                quit()
            case _:
                try:
                    from textual_serve.server import Server
                except ImportError:
                    raise DependencyRequired("web")
                os.environ["MININTERFACE_ENFORCED_WEB"] = '_web-parent'

                server = Server(cmd or " ".join(sys.argv), port=port)
                server.serve()
                quit()
