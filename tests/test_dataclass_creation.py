from dataclasses import dataclass
import sys
from typing import Literal, Optional
from unittest import skipIf

from tyro.conf import FlagConversionOff, OmitArgPrefixes, OmitSubcommandPrefixes, Positional
from mininterface import Tag
from mininterface._lib.dataclass_creation import _unwrap_annotated
from mininterface.cli import Command, SubcommandPlaceholder
from mininterface.exceptions import Cancelled
from mininterface.tag import PathTag, SelectTag
from configs import Annotated, ParametrizedGeneric, Subcommand1, Subcommand2
from shared import MISSING, TestAbstract, runm


from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from configs import SimpleEnv




class TestDataclassCreation(TestAbstract):
    def test_unwrap(self):
        self.assertIs(SimpleEnv, _unwrap_annotated(FlagConversionOff[OmitArgPrefixes[SimpleEnv]]))
        self.assertIs(SimpleEnv, _unwrap_annotated(Annotated[Annotated[SimpleEnv, FlagConversionOff], OmitArgPrefixes] ))