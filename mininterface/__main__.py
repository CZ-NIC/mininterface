from ast import literal_eval
from dataclasses import dataclass
from os import environ
from pathlib import Path
from subprocess import run as srun
from typing import Literal, Optional

from tyro.conf import Positional

from . import run
from .showcase import showcase
from .subcommands import Command
from .tag.flag import File
from .tag.path_tag import PathTag

__doc__ = """Simple GUI/TUI dialog toolkit. Contains:
* dialog commands to output the value the user entered
* commands to operate and test programs using mininterface as a Python library

See the full docs at: https://cz-nic.github.io/mininterface/
"""


Showcase_Type = Literal[1, 2]


# NOTE in the future, allow only some classes (here, the dialog clases) have the shared args
# @dataclass
# class SharedLabel(Command):
#     label: Positional[str]


@dataclass
class Alert(Command):
    """ Dialog: Display the OK dialog with text. """

    label: Positional[str]

    def run(self):
        self._interface.alert(self.label)


@dataclass
class Ask(Command):
    """ Dialog: Prompt the user to input a value.
    By default, we input a str, by the second parameter, you can infer a type,
    ex. `mininterface --ask 'My heading' int`
    """

    label: Positional[str]
    annotation: Positional[Literal["int", "str", "float", "Path", "date", "datetime", "time", "file", "dir"]] = "str"
    """ Impose the given type.
    * Path – any path
    * file – an existing file
    * dir – an existing directory
    Ex. `mininterface ask "Give me a folder" dir` will impose an existing directory to be input. """

    # NOTE
    # validation: Optional[str] = None
    # """ EXPERIMENTAL. Might change, ex. becoming a positional argument."""
    # Filtering the files with certain extension. Allowing only future dates.
    # How it should work? Should it be in annotation or validation?

    def run(self):
        match self.annotation:
            case "int":
                v = int
            case "float":
                v = float
            case "str":
                v = str
            case "Path":
                v = Path
            case "date":
                from datetime import date
                v = date
            case "datetime":
                from datetime import datetime
                v = datetime
            case "time":
                from datetime import time
                v = time
            case "file":
                v = PathTag(is_file=True)
            case "dir":
                v = PathTag(is_dir=True)
            case _:
                raise NotImplementedError(f"This type {self.annotation} has not yet been supported, raise an issue.")
        print(self._interface.ask(self.label, v))


@dataclass
class Confirm(Command):
    """ Dialog: Display confirm box. Returns 0 / 1. """

    label: Positional[str]
    focus: Positional[Literal["yes", "no"]] = "yes"
    """focused button"""

    def run(self):
        r = self._interface.confirm(self.label, self.focus == "yes")
        print(1 if r else 0)


@dataclass
class Select(Command):
    """ Dialog: Prompt the user to select. """
    options: Positional[list[str]]
    label: str = ""

    def run(self):
        print(self._interface.select(self.options, self.label))


@dataclass
class Integrate(Command):
    """ Integrate to the system. Generates a bash completion for the given program. """

    cmd: Positional[File]
    """Path to the program using mininterface.
    Note that Bash completion uses argparse.prog, so do not set prog="Program Name" in the program as bash completion would stop working.
    """

    def run(self):
        environ["MININTERFACE_INTEGRATE_TO_SYSTEM"] = '1'
        srun(self.cmd.absolute(), env=environ)
        quit()


@dataclass
class Showcase:
    """ Prints various form just to show what's possible.
    Choose the interface by MININTERFACE_INTERFACE=...
    Ex. MININTERFACE_INTERFACE=tui mininterface showcase 2
    """
    showcase: Positional[Showcase_Type] = 1


@dataclass
class Web(Command):
    """Expose a program using mininterface to the web."""

    cmd: Positional[File]
    """Path to the program using mininterface."""

    port: int = 64646

    def run(self):
        from .web_interface import WebInterface
        WebInterface(cmd=self.cmd, port=self.port)


def main():
    with run([Alert, Ask, Confirm, Select, Integrate, Showcase,  Web], prog="Mininterface", description=__doc__, ask_for_missing=False) as m:
        pass

    if isinstance(m.env, Showcase):
        # NOTE: GUI does not work well with `Command.run`, the bug with two appearing windows
        showcase(m.env.showcase)


if __name__ == "__main__":
    main()
