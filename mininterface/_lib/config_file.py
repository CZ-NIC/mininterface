from dataclasses import asdict
import dataclasses
import warnings
from pathlib import Path
from typing import Optional, Type


from ..settings import MininterfaceSettings
from .auxiliary import dataclass_asdict_no_defaults, merge_dicts
from .form_dict import EnvClass


def load_settings_from_config(config_file: Path) -> tuple[dict, dict | None]:
    """Load yaml config without tyro. Returns (raw_cli_dict, mininterface_settings_dict).
    raw_cli_dict has the 'mininterface' key already removed."""
    import yaml
    raw = yaml.safe_load(config_file.read_text()) or {}
    return raw, raw.pop("mininterface", None)


def ensure_settings_inheritance(
    base: Optional[MininterfaceSettings], conf: dict, _def_fact=MininterfaceSettings
) -> MininterfaceSettings:
    """Merge a config-file settings dict into MininterfaceSettings.
    Handles direct fields and one level of nested dataclass fields.
    Applies UI inheritance (ui→gui, ui→tui, etc.)."""
    if base:
        conf = merge_dicts(dataclass_asdict_no_defaults(base), conf)
    for sources in [
        ("ui", "gui"),
        ("ui", "tui"),
        ("ui", "tui", "textual"),
        ("ui", "tui", "text"),
        ("ui", "tui", "textual", "web"),
    ]:
        target = sources[-1]
        merged: dict = {}
        for s in sources:
            merged.update(conf.get(s, {}))
        merged.update(conf.get(target, {}))
        if merged:
            conf[target] = merged
    result = base or _def_fact()
    for key, value in conf.items():
        if not hasattr(result, key):
            continue
        attr = getattr(result, key)
        if dataclasses.is_dataclass(attr) and isinstance(value, dict):
            for k2, v2 in value.items():
                if hasattr(attr, k2):
                    setattr(attr, k2, v2)
        else:
            setattr(result, key, value)
    return result


def parse_config_file(
    env_or_list: Type[EnvClass] | list[Type[EnvClass]],
    raw_config: "dict | None" = None,
    config_file: "Path | None" = None,
    **kwargs,
) -> dict:
    """Fill kwargs["default"] from a pre-loaded config dict. Needs tyro.

    Args:
        env_or_list: Class(es) with the configuration.
        raw_config: Pre-loaded yaml dict from load_settings_from_config (mininterface key already removed).
            Pass None when there is no config file.
        config_file: Original path, used only for error messages.
    Kwargs:
        The same as for argparse.ArgumentParser.
    """
    if raw_config is not None and "default" not in kwargs:
        from .dataclass_creation import create_with_missing, to_kebab_case
        try:
            subc = {}

            if isinstance(env_or_list, list):
                kwargs["subcommands_default_union"] = {}
                for cl in env_or_list:
                    cl_name = to_kebab_case(cl.__name__)
                    subc[cl_name] = {}
                    ooo = create_with_missing(cl, raw_config.get(cl_name, {}), subc=subc[cl_name])
                    kwargs["subcommands_default_union"][cl_name] = asdict(ooo)
                    # `kwargs["default"]` remains empty for now as there is no bare default that tyro would support as everything is hidden under the subcommands

            else:
                kwargs["default"] = create_with_missing(env_or_list, raw_config, subc=subc)

            if subc:
                kwargs["subcommands_default"] = subc
        except TypeError:
            raise SyntaxError(f"Config file parsing failed for {config_file}")

    return kwargs


