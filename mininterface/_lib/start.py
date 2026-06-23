# Starting and maintaining a program, using mininterface, in the system.
import sys

from pathlib import Path
from subprocess import run
from typing import Type

from .._mininterface import Mininterface
from ..interfaces import get_interface


class Start:
    def __init__(self, title="", interface: Type[Mininterface] | str | None = None):
        self.title = title
        self.interface = interface

    def integrate(self, env=None):
        """Integrate to the system

        Bash completion uses argparse.prog, so do not set prog="Program Name" as bash completion would stop working.

        NOTE: This is a basic and bash only integration. It might be easily expanded.
        """
        m = get_interface(self.interface, self.title)
        comp_dir = Path("/etc/bash_completion.d/")
        prog = Path(sys.argv[0]).name
        target = comp_dir / prog

        if comp_dir.exists():
            if target.exists():
                m.alert(f"Destination {target} already exists. Exit.")
                return
            if m.confirm(f"We generate the bash completion into {target}"):
                run(["sudo", "-E", sys.argv[0], "--tyro-write-completion", "bash", target])
                m.alert(f"Integration completed. Start a bash session to see whether bash completion is working.")
                return

        m.alert("Cannot auto-detect. Use --tyro-print-completion {bash/zsh/tcsh} to get the sh completion script.")
