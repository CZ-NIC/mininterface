from dataclasses import dataclass, field
import importlib
from typing import Literal, Optional, TypeVar

from .exceptions import ValidationFail

from .subcommands import Command

from . import run
from .showcase import showcase

from typing import get_args, get_origin, Optional, Union, List, Dict

from tyro.conf import Positional

__doc__ = """Simple GUI/TUI dialog. Outputs the value the user entered. See the full docs at: https://cz-nic.github.io/mininterface/"""

TYPE_MAP = ({
    "int": int,
    "str": str,
    "float": float,
})


def resolve_type(type_str: str):
    try:
        return TYPE_MAP[type_str]
    except KeyError:
        print(f"Unknown type {type_str}")
        quit()


@dataclass
class Web:
    """Launch a miniterface program, while the TextualInterface will be exposed to the web. """

    cmd: str = ""
    """Path to a program, using mininterface."""

    port: int = 64646


Showcase = Literal[1] | Literal[2]


# NOTE in the future, allow only some classes (here, the dialog clases) have the shared args
# @dataclass
# class SharedLabel(Command):
#     label: Positional[str]


@dataclass
class Alert(Command):
    """ Display the OK dialog with text. """

    label: Positional[str]

    def run(self):
        self._interface.alert(self.label)


@dataclass
class Ask(Command):
    """ Prompt the user to input a value.
    By default, we input a str, by the second parameter, you can infer a type,
    ex. `mininterface --ask 'My heading' int`
    """

    label: Positional[str]

    def run(self):
        self._interface.ask(self.label)


@dataclass
class OtherDialog(Command):
    """ A dialog TODO """
    cmda: str

    def run(self):
        pass


@dataclass
class Dialog():
    """ A dialog TODO """
    cmd: Ask | Alert
    # dva: OtherDialog


@dataclass
class CliInteface:
    web: Web
    alert: str = ""
    """ Display the OK dialog with text. """
    ask: str | tuple[str, str] = ""
    """ Prompt the user to input a value.
    By default, we input a str, by the second parameter, you can infer a type,
    ex. `mininterface --ask 'My heading' int`
    """
    confirm: str = ""
    """ Display confirm box, focusing 'yes'. """
    confirm_default_no: str = ""
    """ Display confirm box, focusing 'no'. """
    select: list = field(default_factory=list)
    """ Prompt the user to select. """

    showcase: Optional[Showcase] = None
    """ Prints various form just to show what's possible.
    Choose the interface by MININTERFACE_INTERFACE=...
    Ex. MININTERFACE_INTERFACE=tui mininterface --showcase 2
    """


def web(env: Web):
    from .web_interface import WebInterface
    WebInterface(cmd=env.cmd, port=env.port)


def main():
    result = []
    # We tested both GuiInterface and TextualInterface are able to pass a variable to i.e. a bash script.
    # NOTE TextInterface fails (`mininterface --ask Test | grep Hello` – pipe causes no visible output).
    # TODO
    # with run(Dialog, prog="Mininterface", description=__doc__) as m:
    with run([Alert, Ask, OtherDialog], prog="Mininterface", description=__doc__) as m:
        pass
        print("135: m", m.env)  # TODO

    print("TODO end")
    return

    with run(CliInteface, prog="Mininterface", description=__doc__) as m:
        for method, label in vars(m.env).items():
            if method in ["web", "showcase"]:  # processed later
                continue
            if method == "select" and label:
                result.append(m.select(options=label))
            elif method == "ask" and label:
                if isinstance(label, tuple):
                    arg, type_ = label[0], resolve_type(label[1])
                    if not type_:
                        print(f"Unknown type {type_}")
                        quit()
                    result.append(m.ask(arg, type_))
                else:
                    m.ask(label)
            elif method == "confirm_default_no" and label:
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
        showcase(m.env.showcase)


if __name__ == "__main__":
    main()
