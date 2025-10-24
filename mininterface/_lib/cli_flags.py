from argparse import ArgumentParser
import logging
import sys
from typing import Optional, Sequence

from tyro.conf import FlagConversionOff

from .form_dict import EnvClass

from typing import List, Any, Optional

from tyro._fields import FieldDefinition
from tyro.conf._confstruct import _ArgConfig


class CliFlags:

    _add_verbose: bool = False
    version: str = ""
    _add_quiet: bool = False

    default_verbosity: int = logging.WARNING
    _verbosity_sequence: Optional[Sequence[int]] = None

    config: bool = False

    def __init__(
        self,
        add_verbose: bool | int | Sequence[int] = False,
        add_version: Optional[str] = None,
        add_version_package: Optional[str] = None,
        add_quiet: bool = False,
        add_config: bool = False,
    ):
        self._enabled = {"verbose": True, "version": True, "quiet": True, "config": True}
        # verbosity
        match add_verbose:
            case bool():
                self._add_verbose = add_verbose
            case int():
                self._add_verbose = True
                self.default_verbosity = add_verbose
                self._verbosity_sequence = list(range(add_verbose - 10, -1, -10))
            case list() | tuple():
                self._add_verbose = True
                self.default_verbosity = add_verbose[0]
                self._verbosity_sequence = add_verbose[1:]
        self._add_quiet = add_quiet

        # version
        if add_version:
            self.version = add_version
        elif add_version_package:
            try:
                from importlib.metadata import PackageNotFoundError, version
            except ImportError:
                self.version = f"cannot determine version"
            try:
                self.version = version(add_version_package)
            except PackageNotFoundError:
                self.version = f"package {add_version_package} not found"

        # config
        self.config = add_config

        self.orig_stream = (
            sys.stderr
        )  # NOTE might be removed now. Might be used if we redirect_stderr while setting basicConfig.

        self.field_list: list[FieldDefinition] = []
        """ List of FieldDefinitions corresponding to the arguments added via this helper"""

        self.arguments_prepared: list[dict[str, Any]] = []
        self.setup_done = False
        """ Setup might be called multiple times – ex. parsing fails and we call tyro.cli in recursion. """

    def should_add(self, env_classes: list[EnvClass]) -> bool:
        # Flags are added only if neither the env_class nor any of the subcommands have the same-name flag already
        self._enabled["verbose"] = self._add_verbose and self._attr_not_present("verbose", env_classes)
        self._enabled["quiet"] = self._add_quiet and self._attr_not_present("quiet", env_classes)
        self._enabled["version"] = self.version and self._attr_not_present("version", env_classes)
        self._enabled["config"] = self.config and self._attr_not_present("config", env_classes)

        return self.add_verbose or self.add_version or self.add_quiet or self.add_config

    def _attr_not_present(self, flag, env_classes):
        return all(flag not in cl.__annotations__ for cl in env_classes)

    @property
    def add_verbose(self):
        return self._add_verbose and self._enabled["verbose"]

    @property
    def add_version(self):
        return self.version and self._enabled["version"]

    @property
    def add_quiet(self):
        return self._add_quiet and self._enabled["quiet"]

    @property
    def add_config(self):
        return self.config and self._enabled["config"]

    def get_log_level(self, count):
        """
        Ex.
        * add_verbose = True ( default level = WARNING )
            * -v -> logging.INFO
            * -vv -> logging.DEBUG
            * -vvv -> logging.NOTSET
        * add_verbose = default level INFO
            * -v -> logging.DEBUG
            * -vv -> logging.NOTSET
        * add_verbose = (40, 35, 30, 25)
            * -v -> 35
            * -vv -> logging.INFO
            * -vvv -> 25
            * -vvv -> logging.NOTSET

        Args:
            count: number of times `--verbose` flag is used. Negative count means the `--quiet` flag is used.

        Returns:
            int: log level
        """
        if count == -1:  # quiet flag
            return logging.ERROR
        if not count:
            return self.default_verbosity
        if not self._verbosity_sequence:
            seq = logging.INFO, logging.DEBUG
        else:
            seq = self._verbosity_sequence
        log_level = {i + 1: level for i, level in enumerate(seq)}.get(count, logging.NOTSET)
        return log_level

    def add_typed_argument(
        self,
        prefix: str,
        *aliases: str,
        action: Optional[str] = None,
        default: Any = False,
        helptext: Optional[str] = None,
        metavar: Optional[str] = None,
        version: Optional[str] = None,
    ) -> FieldDefinition:
        # Prepare FieldDefinition
        name = aliases[0]
        aliases_ = tuple((prefix * (1 if len(n) == 1 else 2) + n) for n in aliases) if aliases else None
        typ_ = bool if action in ("store_true", "store_false") else int if action == "count" else str

        field = FieldDefinition(
            intern_name=name,
            extern_name=name,
            type=typ_,
            type_stripped=typ_,
            default=default,
            helptext=helptext,
            markers={FlagConversionOff},
            custom_constructor=False,
            argconf=_ArgConfig(
                name=aliases_[0],
                metavar="",
                help=helptext,
                help_behavior_hint="",
                aliases=aliases_[1:] or None,
                prefix_name=False,
                constructor_factory=None,
                default=default,
            ),
            mutex_group=None,
            call_argname=name,
        )

        self.field_list.append(field)

        # prepare argparse
        self.arguments_prepared.append(
            {
                "field": field,
                "names": aliases_,
                "kwargs": {
                    "action": action,
                    "default": default,
                    "help": helptext,
                    "metavar": metavar,
                    "version": version,
                },
            }
        )

        return field

    def setup(self, parser: ArgumentParser):
        if self.setup_done:
            # tyro.cli might be called multiple times if some missing required fields
            return
        self.setup_done = True
        prefix = "-" if "-" in parser.prefix_chars else parser.prefix_chars[0]
        if self.add_verbose:
            self.add_typed_argument(
                prefix,
                "verbose",
                "v",
                action="count",
                default=0,
                helptext="verbosity level, can be used multiple times to increase",
            )

        if self.add_version:
            self.add_typed_argument(
                prefix,
                "version",
                action="version",
                version=self.version,
                default="",
                helptext=f"show program's version number ({self.version}) and exit",
            )

        if self.add_quiet:
            self.add_typed_argument(
                prefix, "quiet", "q", action="store_true", helptext="suppress warnings, display only errors"
            )

        if self.add_config:
            self.add_typed_argument(
                prefix, "config", helptext=f"path to config file to fetch the defaults from", metavar="PATH"
            )

    def apply_to_parser(self, parser):
        for item in self.arguments_prepared:
            kwargs = {k: v for k, v in item["kwargs"].items() if v is not None}
            parser.add_argument(*item["names"], **kwargs)
