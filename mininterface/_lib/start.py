# Starting and maintaining a program, using mininterface, in the system.
import sys
from collections import defaultdict
from dataclasses import is_dataclass
from pathlib import Path
from subprocess import run
from typing import Optional, Type
from warnings import warn

from .._mininterface import Mininterface
from ..exceptions import DependencyRequired
from ..interfaces import get_interface
from ..cli import Command, SubcommandPlaceholder
from ..tag import Tag
from .form_dict import DataClass, EnvClass, TagDict, dataclass_to_tagdict

try:
    from .cli_parser import parse_cli
except DependencyRequired as e:
    parse_cli = e


class Start:
    def __init__(self, title="", interface: Type[Mininterface] | str | None = None):
        self.title = title
        self.interface = interface

    def integrate(self, env=None):
        """ Integrate to the system

        Bash completion uses argparse.prog, so do not set prog="Program Name" as bash completion would stop working.

        NOTE: This is a basic and bash only integration. It might be easily expanded.
        """
        m = get_interface(self.interface, self.title)
        comp_dir = Path("/etc/bash_completion.d/")
        prog = Path(sys.argv[0]).name
        target = comp_dir/prog

        if comp_dir.exists():
            if target.exists():
                m.alert(f"Destination {target} already exists. Exit.")
                return
            if m.confirm(f"We generate the bash completion into {target}"):
                run(["sudo", "-E", sys.argv[0], "--tyro-write-completion", "bash", target])
                m.alert(f"Integration completed. Start a bash session to see whether bash completion is working.")
                return

        m.alert("Cannot auto-detect. Use --tyro-print-completion {bash/zsh/tcsh} to get the sh completion script.")


class ChooseSubcommandOverview:
    def __init__(self, env_classes: list[Type[DataClass]], m: Mininterface[EnvClass], args, ask_for_missing=True):
        self.m = m
        superform: TagDict = {}
        # remove placeholder as we do not want it to be in the form
        env_classes = [e for e in env_classes if e is not SubcommandPlaceholder]

        # Subcommands might be inherited from the same base class, they might have some common fields
        # that has meaning for all subcommands (like `--output-filename`).
        # In the current implementation, common fields works only if all of the classes have the same base.
        # It does not implement nested fields.
        common_bases = set.intersection(*(set(c for c in cl.__mro__ if is_dataclass(c)) for cl in env_classes))
        common_bases.discard(Command)  # no interesting fields and to prevent printing an empty --help with it
        common_fields = [field for cl in common_bases for field in cl.__annotations__]
        common_fields_missing_defaults = {}
        """ If a common field is missing, store its value here. """

        # Process help
        # The help should produce only shared arguments
        if "--help" in args and len(common_bases):
            parse_cli(next(iter(common_bases)), {}, False, True, args=args)
            raise NotImplementedError("We should never come here. Help failed.")

        # Raise a form with all the subcommands in groups
        for env_class in env_classes:
            form, wf = parse_cli(env_class, {}, False, ask_for_missing, args=args)

            if wf:  # We have some wrong fields.
                if not common_fields_missing_defaults:
                    # Store the values for the common fields
                    # NOTE this will work poorly when we ask for a not common fields in the first class
                    common_fields_missing_defaults = m.form(wf)
                else:  # As the common field appears multiple times, restore its value.
                    for tag_name, val in common_fields_missing_defaults.items():
                        wf[tag_name]._set_val(val)
                        del wf[tag_name]
                    if wf:  # some other fields were missing too
                        # NOTE It makes no sense to ask for wrong fields for env classes
                        # that will not be run.
                        m.form(wf)

            if isinstance(form, Command):
                form: Command
                form.facet = m.facet
                form.interface = m
                # Undocumented as I'm not sure whether I can recommend it or there might be a better design.
                # Init is launched before tagdict creation so that it can modify class __annotation__.
                form.init()

            tags = dataclass_to_tagdict(form)

            # Pull out common fields to the common level
            # Ex. base class has the PathTag field `files`. Hence all subcommands have a copy of this field.
            # We create a single PathTag tag and then source all children PathTags to it.
            for cf in common_fields:
                local: Tag = tags[""].pop(cf)
                if cf not in superform:
                    superform[cf] = type(local)(**local.__dict__)
                superform[cf]._src_obj_add(local)

            name = form.__class__.__name__
            # if isinstance(form, Command):
            # add the button to submit just that one dataclass,
            # sets m.env to it,
            # and possibly call Command.run
            tags[""][name] = Tag(self._submit_generated_button(form))
            superform[name] = tags

        # this call will a chosen env will trigger its `.run()` and stores a chosen env to `m.env`
        m.form(superform, submit=False)
        # NOTE m.env should never be None after this form call... except in testing.
        # The testing should adapt the possibility.
        # Then, I'd like to have this line here:
        # assert m.env is not None

    def _submit_generated_button(self, form: EnvClass):
        def _():
            self.m.env = form
            if isinstance(form, Command):
                form.run()
        return _
