""" Its name is not test_minimal.py because it fails when at least [basic] bundle is installed. """

from dataclasses import dataclass
from mininterface import DependencyRequired
from .shared import TestAbstract, runm


@dataclass
class Env:
    test: bool = False


class TestMinimal(TestAbstract):
    def test_raise(self):
        # some cases hard exits the program
        # as it does not make sense to conitnue
        # in such case, DependencyRequired wraps into SystemExit
        with self.assertRaises(SystemExit) as cm:
            runm(Env)
        self.assertEqual(
            "Install the missing dependency by running: pip install mininterface[basic]", str(cm.exception))

        # other cases are recoverable
        with self.assertRaises(DependencyRequired):
            from mininterface.cli import Command

        # however, the basic dialogs must still work
        self.assertEqual(0, runm().ask("", int))
