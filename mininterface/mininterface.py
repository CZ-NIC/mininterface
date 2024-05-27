#!/usr/bin/env python3
from argparse import ArgumentParser
from tkinter import TclError

from tyro import cli
from tyro.extras import get_parser

from mininterface.HeadlessInterface import HeadlessInterface, OutT
from mininterface.GuiInterface import GuiInterface
from mininterface.TuiInterface import TuiInterface, ReplInterface


def run(*args,  interface: HeadlessInterface = None, **kwargs):
    parser: ArgumentParser = get_parser(*args, **kwargs)
    args: OutT = cli(*args, **kwargs)
    try:
        interface: GuiInterface | HeadlessInterface = interface or GuiInterface(parser, args)
    except TclError:  # Fallback to a different interface
        interface = ReplInterface(parser, args)
    return interface
