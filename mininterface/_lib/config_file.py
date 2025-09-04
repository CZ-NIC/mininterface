import warnings
from pathlib import Path
from typing import Optional, Type

from ..settings import MininterfaceSettings
from .auxiliary import dataclass_asdict_no_defaults, merge_dicts
from .dataclass_creation import create_with_missing
from .form_dict import EnvClass

try:
    import yaml
    from tyro._singleton import MISSING_NONPROP
except ImportError:
    from ..exceptions import DependencyRequired

    raise DependencyRequired("basic")

def parse_config_file(
    env_or_list: Type[EnvClass] | list[Type[EnvClass]],
    config_file: Path | None = None,
    settings: Optional[MininterfaceSettings] = None,
    **kwargs,
) -> tuple[dict, MininterfaceSettings | None]:
    """Fetches the config file into the program defaults kwargs["default"] and UI settings.

    Args:
        env_class: Class with the configuration.
        config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
        settings: Used to complement the 'mininterface' config file section-
    Kwargs:
        The same as for argparse.ArgumentParser.

    Returns:
        Tuple of kwargs and settings.
    """
    if isinstance(env_or_list, list):
        subcommands, env = env_or_list, None
    else:
        subcommands, env = None, env_or_list

    # Load config file
    if config_file and subcommands:
        # Reading config files when using subcommands is not implemented.
        # NOTE But might be now.
        kwargs.pop("default", None)
        warnings.warn(
            f"Config file {config_file} is ignored because subcommands are used."
            " It is not easy to set how this should work."
            " Describe the developer your usecase so that they might implement this."
        )

    if "default" not in kwargs and not subcommands and config_file:
        # Undocumented feature. User put a namespace into kwargs["default"]
        # that already serves for defaults. We do not fetch defaults yet from a config file.
        disk = yaml.safe_load(config_file.read_text()) or {}  # empty file is ok
        try:
            if confopt := disk.pop("mininterface", None):
                # Section 'mininterface' in the config file.
                settings = _merge_settings(settings, confopt)

            kwargs["default"] = create_with_missing(env, disk)
        except TypeError:
            raise SyntaxError(f"Config file parsing failed for {config_file}")

    return kwargs, settings


def _merge_settings(
    runopt: MininterfaceSettings | None, confopt: dict, _def_fact=MininterfaceSettings
) -> MininterfaceSettings:
    # Settings inheritance:
    # Config file > program-given through run(settings=) > the default settings (original dataclasses)

    # Assure the default settings
    # Either the program-given or create fresh defaults
    if runopt:
        # Merge the program-given settings to the config file settings if not yet present.
        confopt = merge_dicts(dataclass_asdict_no_defaults(runopt), confopt)
    else:
        runopt = _def_fact()

    # Merge option sections.
    # Ex: TextSettings will derive from both Tui and Ui. You may specify a Tui default value, common for all Tui interfaces.
    for sources in [
        ("ui", "gui"),
        ("ui", "tui"),
        ("ui", "tui", "textual"),
        ("ui", "tui", "text"),
        ("ui", "tui", "textual", "web"),
    ]:
        target = sources[-1]
        confopt[target] = {
            **{k: v for s in sources for k, v in confopt.get(s, {}).items()},
            **confopt.get(target, {}),
        }

    for key, value in vars(create_with_missing(_def_fact, confopt)).items():
        if value is not MISSING_NONPROP:
            setattr(runopt, key, value)
    return runopt