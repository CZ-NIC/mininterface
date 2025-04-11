import sys
from dataclasses import dataclass, field
from typing import Literal, Optional

from tyro.conf import FlagConversionOff

from . import Mininterface, run
from .exceptions import DependencyRequired
from .showcase import ChosenInterface, showcase

__doc__ = """Simple GUI/TUI dialog. Outputs the value the user entered. See the full docs at: https://cz-nic.github.io/mininterface/"""


@dataclass
class Web:
    """Launch a miniterface program, while the TextualInterface will be exposed to the web.

    NOTE Experimenal undocumented feature. """

    cmd: str = ""
    """Path to a program, using mininterface."""

    port: int = 64646


Showcase = Literal[1] | Literal[2]


@dataclass
class CliInteface:
    web: Web
    alert: str = ""
    """ Display the OK dialog with text. """
    ask: str = ""
    """ Prompt the user to input a text.  """
    ask_number: str = ""
    """ Prompt the user to input a number. Empty input = 0. """
    confirm: str = ""
    """ Display confirm box, focusing 'yes'. """
    confirm_default_no: str = ""
    """ Display confirm box, focusing 'no'. """
    choice: list = field(default_factory=list)
    """ Prompt the user to select. """

    showcase: Optional[tuple[ChosenInterface, Showcase]] = None
    """ Prints various form just to show what's possible."""


def web(env: Web):
    from .web_interface import WebInterface
    WebInterface(cmd=env.cmd, port=env.port)


def main():
    result = []
    # We tested both GuiInterface and TextualInterface are able to pass a variable to i.e. a bash script.
    # NOTE TextInterface fails (`mininterface --ask Test | grep Hello` – pipe causes no visible output).
    with run(CliInteface, prog="Mininterface", description=__doc__) as m:
        for method, label in vars(m.env).items():
            if method in ["web", "showcase"]:  # processed later
                continue
            if method == "confirm_default_no" and label:
                result.append(m.confirm(label, False))
            elif label:
                result.append(getattr(m, method)(label))

    # Displays each result on a new line. Currently, this is an undocumented feature.
    # As we use the script for a single value only and it is not currently possible
    # to ask two numbers or determine a dialog order etc.
    [print(val) for val in result]

    if m.env.web.cmd:
        web(m.env.web)
    if m.env.showcase:
        showcase(*m.env.showcase)


if __name__ == "__main__":
    main()
