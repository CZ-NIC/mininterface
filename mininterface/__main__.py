from dataclasses import dataclass

from .common import DependencyRequired

from . import run, Mininterface

__doc__ = """Simple GUI dialog. Outputs the value the user entered."""


@dataclass
class Web:
    """ Experimenal undocumented feature. """

    cmd: str
    """ Launch a miniterface program, while the TextualInterface will be exposed to the web."""
    # NOTE: The textual app ends after the first submit. We have to correct that before the web makes sense.
    # with run(interface=TextualInterface) as m:
    #   m.form({"hello": 1})  # the app ends here
    #   m.form({"hello": 2})  # we never get here

    port: int = 64646


@dataclass
class CliInteface:
    web: Web
    alert: str = ""
    """ Display the OK dialog with text. """
    ask: str = ""
    """ Prompt the user to input a text.  """
    ask_number: str = ""
    """ Prompt the user to input a number. Empty input = 0. """
    is_yes: str = ""
    """ Display confirm box, focusing 'yes'. """
    is_no: str = ""
    """ Display confirm box, focusing 'no'. """


def web(m: Mininterface):
    try:
        from textual_serve.server import Server
    except ImportError:
        raise DependencyRequired("web")
    server = Server(m.env.web.cmd, port=m.env.web.port)
    server.serve()


def main():
    result = []
    # We tested both GuiInterface and TextualInterface are able to pass a variable to i.e. a bash script.
    # NOTE TextInterface fails (`mininterface --ask Test | grep Hello` – pipe causes no visible output).
    with run(CliInteface, prog="Mininterface", description=__doc__) as m:
        for method, label in vars(m.env).items():
            if method == "web":  # processed later
                continue
            if label:
                result.append(getattr(m, method)(label))

    # Displays each result on a new line. Currently, this is an undocumented feature.
    # As we use the script for a single value only and it is not currently possible
    # to ask two numbers or determine a dialog order etc.
    [print(val) for val in result]

    if m.env.web:
        web(m)


if __name__ == "__main__":
    main()
