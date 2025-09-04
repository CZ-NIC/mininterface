from mininterface import Mininterface, run
from mininterface._lib.cli_parser import parse_cli
from mininterface._lib.config_file import _merge_settings, parse_config_file
from mininterface.settings import UiSettings
from mininterface.tag import PathTag, Tag
from attrs_configs import AttrsNested
from configs import AnnotatedClass, FurtherEnv2, MissingCombined, MissingNonscalar, MissingPositional, MissingPositionalScalar, MissingUnderscore, SimpleEnv
from dumb_settings import GuiSettings, MininterfaceSettings, TextSettings, TextualSettings, TuiSettings, UiSettings as UiDumb, WebSettings
from pydantic_configs import PydNested
from shared import MISSING, TestAbstract, runm


import os
import sys
import warnings
from argparse import ArgumentParser
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from subprocess import run as srun
from tyro.conf import FlagConversionOff, OmitArgPrefixes

# When testing on a machine with display, a GUI would be used and stuck.
os.environ["MININTERFACE_INTERFACE"] = "min"


def r(*args):
    return srun(args, capture_output=True, text=True).stdout.strip()


class TestMain(TestAbstract):
    def test_main(self):
        self.assertEqual("Asking: Hello world", r("mininterface", "ask", "Hello world"))
        self.assertEqual("Asking yes: foo\n1", r("mininterface", "confirm", "foo"))
        self.assertEqual("Asking no: foo\n0", r("mininterface", "confirm", "foo", "no"))
