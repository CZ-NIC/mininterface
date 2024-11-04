# Starting and maintaining a program, using mininterface, in the system.
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Type
from subprocess import run

from .mininterface import Mininterface
from .common import InterfaceNotAvailable
from .text_interface import TextInterface


# Import optional interfaces
try:
    from .tk_interface import TkInterface
except ImportError:
    if TYPE_CHECKING:
        pass  # Replace TYPE_CHECKING with `type GuiInterface = None` since Python 3.12
    else:
        TkInterface = None
try:
    from .textual_interface import TextualInterface
except ImportError:
    TextualInterface = None

GuiInterface = TkInterface
TuiInterface = TextualInterface or TextInterface


def get_interface(title="", interface: Type[Mininterface] | str | None = None, env=None):
    try:
        if interface == "tui":  # undocumented feature
            interface = TuiInterface
        elif interface == "gui":  # undocumented feature
            interface = GuiInterface
        if interface is None:
            raise InterfaceNotAvailable  # GuiInterface might be None when import fails
        else:
            interface = interface(title, env)
    except InterfaceNotAvailable:  # Fallback to a different interface
        interface = TuiInterface(title, env)
    return interface


def integrate(title="", interface: Type[Mininterface] | str | None = None, env=None):
    """ Integrate to the system

    Bash completion uses argparse.prog, so do not set prog="Program Name" as bash completion would stop working.

    NOTE: This is a basic and bash only integration. It might be easily expanded.
    """
    m = get_interface(title, interface)
    comp_dir = Path("/etc/bash_completion.d/")
    prog = Path(sys.argv[0]).name
    target = comp_dir/prog

    if comp_dir.exists():
        if target.exists():
            m.alert(f"Destination {target} already exists. Exit.")
            return
        if m.is_yes(f"We generate the bash completion into {target}"):
            run(["sudo", "-E", sys.argv[0], "--tyro-write-completion", "bash", target])
            m.alert(f"Integration completed. Start a bash session to see whether bash completion is working.")
            return

    m.alert("Cannot auto-detect. Use --tyro-print-completion {bash/zsh/tcsh} to get the sh completion script.")
