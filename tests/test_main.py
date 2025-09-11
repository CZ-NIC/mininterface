from shared import TestAbstract


import os
from subprocess import run as srun

# When testing on a machine with display, a GUI would be used and stuck.
os.environ["MININTERFACE_INTERFACE"] = "min"


def r(*args):
    return srun(args, capture_output=True, text=True).stdout.strip()


class TestMain(TestAbstract):
    def test_main(self):
        self.assertEqual("Asking: Hello world", r("mininterface", "ask", "Hello world"))
        self.assertEqual("Asking yes: foo\n1", r("mininterface", "confirm", "foo"))
        self.assertEqual("Asking no: foo\n0", r("mininterface", "confirm", "foo", "no"))
