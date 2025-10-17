from dataclasses import asdict
import warnings
from pathlib import Path
from typing import Optional, Type


from ..settings import MininterfaceSettings
from .auxiliary import dataclass_asdict_no_defaults, merge_dicts
from .dataclass_creation import create_with_missing, to_kebab_case
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
    **kwargs,
) -> tuple[dict, dict | None]:
    """Fetches the config file into the program defaults kwargs["default"] and UI settings.

    Args:
        env_or_list: Class(es) with the configuration.
        config_file: File to load YAML to be merged with the configuration.
            You do not have to re-define all the settings in the config file, you can choose a few.
    Kwargs:
        The same as for argparse.ArgumentParser.

    Returns:
        Tuple of kwargs and dict (section 'mininterface' in the config file).
    """
    confopt = None
    if "default" not in kwargs and config_file:
        # Undocumented feature. User put a namespace into kwargs["default"]
        # that already serves for defaults. We do not fetch defaults yet from a config file.
        disk = yaml.safe_load(config_file.read_text()) or {}  # empty file is ok
        try:
            confopt = disk.pop("mininterface", None)
            subc = {}

            if isinstance(env_or_list, list):
                kwargs["subcommands_default_union"] = {}
                for cl in env_or_list:
                    cl_name = to_kebab_case(cl.__name__)
                    subc[cl_name] = {}
                    ooo = create_with_missing(cl, disk.get(cl_name, {}), subc=subc[cl_name])
                    kwargs["subcommands_default_union"][cl_name] = asdict(ooo)
                    # `kwargs["default"]` remains empty for now as there is no bare default that tyro would support as everything is hidden under the subcommands

            else:
                kwargs["default"] = create_with_missing(env_or_list, disk, subc=subc)

            if subc:
                kwargs["subcommands_default"] = subc
        except TypeError:
            raise SyntaxError(f"Config file parsing failed for {config_file}")

    return kwargs, confopt


def ensure_settings_inheritance(
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
