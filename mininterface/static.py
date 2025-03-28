from dataclasses import fields


def dataclass_asdict_no_defaults(obj) -> dict:
    """ Ignore the dataclass default values. """
    if not hasattr(obj, "__dataclass_fields__"):
        return obj

    result = {}
    for field in fields(obj):
        field_value = getattr(obj, field.name)
        default_value = field.default
        if field_value != default_value:
            if hasattr(field_value, "__dataclass_fields__"):
                result[field.name] = dataclass_asdict_no_defaults(field_value)
            else:
                result[field.name] = field_value
    return result


def merge_dicts(d1: dict, d2: dict):
    """ Recursively merge second dict to the first. """
    for key, value in d2.items():
        if isinstance(value, dict) and isinstance(d1.get(key), dict):
            merge_dicts(d1[key], value)
        else:  # replace / insert value
            d1[key] = value
    return d1
