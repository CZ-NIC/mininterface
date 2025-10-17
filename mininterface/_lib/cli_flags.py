from functools import lru_cache
import logging
from dataclasses import dataclass
from typing import Optional, Sequence

from .form_dict import EnvClass


class CliFlags:

    _add_verbose: bool = False
    version: bool | str = False
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
