import logging
import sys
from typing import Optional, Sequence

from tyro.conf import FlagConversionOff, FlagCreatePairsOff, UseCounterAction

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
    ) -> FieldDefinition:
        # Prepare FieldDefinition
        name = aliases[0]
        aliases_ = tuple((prefix * (1 if len(n) == 1 else 2) + n) for n in aliases) if aliases else None
        typ_ = bool if action in ("store_true", "store_false") else int if action == "count" else str

        # Markers drive the lowering when the FieldDefinition is parsed by the native
        # tyro backend (with the argparse backend, parsing is done by parser.add_argument
        # and the FieldDefinition is used for the helptext only).
        if action == "count":
            markers = {UseCounterAction}
        elif action in ("store_true", "store_false"):
            markers = {FlagCreatePairsOff}
        else:
            markers = {FlagConversionOff}

        field = FieldDefinition(
            intern_name=name,
            extern_name=name,
            type=typ_,
            type_stripped=typ_,
            default=default,
            helptext=helptext,
            markers=markers,
            custom_constructor=False,
            argconf=_ArgConfig(
                name=aliases_[0],
                metavar=metavar or "",
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

        return field

    def setup(self):
        """Build the field_list; the fields are then injected into the ParserSpecification
        in tyro_patches.tyro_parse_args."""
        if self.setup_done:
            # tyro.cli might be called multiple times if some missing required fields
            return
        self.setup_done = True
        prefix = "-"
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
            # The flag itself is handled by a pre-scan in tyro_patches.tyro_parse_args,
            # the field serves the helptext.
            self.add_typed_argument(
                prefix,
                "version",
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

    def consume_output(self, out: dict):
        """Pop our injected flags from the parsed output dict
        (so that they do not reach the env dataclass construction) and apply them."""
        if self.add_verbose and "verbose" in out:
            verbose = out.pop("verbose") or 0
            self.apply_verbosity(verbose)
        if self.add_quiet and "quiet" in out:
            if out.pop("quiet"):
                self.apply_verbosity(-1, quiet=True)
        if self.add_version:
            out.pop("version", None)
        if self.add_config:
            out.pop("config", None)

    def apply_verbosity(self, count: int, quiet=False):
        """Set up the root logger according to the number of -v flags (or -q for count=-1)."""
        root = logging.getLogger()
        if quiet:
            new_level = self.get_log_level(-1)
            if not root.handlers:
                logging.basicConfig(level=new_level, format="%(message)s", stream=self.orig_stream)
            else:
                root.setLevel(new_level)
                for handler in root.handlers:
                    if handler.level < new_level:  # edit just benevolent handlers
                        handler.setLevel(new_level)
            return
        if not root.handlers:
            level = self.get_log_level(count) if count > 0 else self.default_verbosity
            logging.basicConfig(level=level, format="%(message)s", stream=self.orig_stream)
        elif count > 0:
            level = self.get_log_level(count)
            root.setLevel(level)
            for handler in root.handlers:
                if handler.level > level:  # increase verbosity for strict handlers
                    handler.setLevel(level)
