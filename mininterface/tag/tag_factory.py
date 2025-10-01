from copy import copy
from datetime import date, time
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Literal, Type, get_args, get_origin, get_type_hints

from annotated_types import BaseMetadata, GroupedMetadata, Len

from . import DatetimeTag, SelectTag, Tag
from .callback_tag import CallbackTag
from .path_tag import PathTag
from .tag import TagValue, ValidationCallback
from .type_stubs import TagCallback


def _get_annotation_from_class_hierarchy(cls, key):
    for base in cls.__mro__:
        if key in getattr(base, "__annotations__", {}):
            return base.__annotations__[key]
    return None


def get_type_hint_from_class_hierarchy(cls, key):
    for base in cls.__mro__:
        hints = get_type_hints(base)
        if key in hints:
            return hints[key]
    return None


def _get_tag_type(tag: Tag) -> Type[Tag]:
    """Return the most specific Tag child that a tag value can be expressed with.
    Ex. Return PathTag for a Tag having a Path as a value.
    """
    pt = tag._get_possible_types()
    if len(pt) == 1 and pt[0][0] is Literal:
        return SelectTag
    if tag._is_subclass(Path):
        return PathTag
    if tag._is_subclass(date) or tag._is_subclass(time):
        return DatetimeTag
    if tag._is_subclass(Enum):
        return SelectTag
    return type(tag)


def assure_tag(
    type_or_tag: Type[TagValue] | Tag, validation: Iterable[ValidationCallback] | ValidationCallback | None = None
) -> Tag:
    if isinstance(type_or_tag, Tag):
        if validation:
            type_or_tag._add_validation(validation)
        return type_or_tag
    else:
        return tag_assure_type(Tag(annotation=type_or_tag, validation=validation))


def tag_assure_type(tag: Tag):
    """morph to correct class `Tag("", annotation=Path)` -> `PathTag("", annotation=Path)`"""
    if (type_ := _get_tag_type(tag)) is not Tag and not isinstance(tag, type_):
        # I cannot use type_._fetch_from(tag) here as SelectTag.__post_init__
        # needs the self.val which would not be yet set.
        # Hence we pass the attributes as a dict, while fixing the inheritance – we need to inherit
        # directly from the source tag (not from its own ancestors).
        info = {**tag.__dict__}
        info["_src_obj"] = tag
        return type_(**info)
    return tag


def tag_factory(
    val=None, description=None, annotation=None, *args, _src_obj=None, _src_key=None, _src_class=None, **kwargs
):
    if _src_obj and not _src_class:
        # NOTE it seems _src_obj is sometimes accepts Type[DataClass], and not a DataClass,
        # unless I find out why, here is the workaround:
        if isinstance(_src_obj, type):  # form is a class, not an instance
            _src_class = _src_obj
        else:
            _src_class = _src_obj.__class__
    kwargs |= {"_src_obj": _src_obj, "_src_key": _src_key, "_src_class": _src_class}
    validators = []
    tag = None
    if _src_class:
        if not annotation:  # when we have _src_class, we assume to have _src_key too
            annotation = get_type_hint_from_class_hierarchy(_src_class, _src_key)
            if annotation is TagCallback:
                return CallbackTag(val, description, *args, **kwargs)
            else:
                # We now have annotation from `field: list[Path]` or `field: Annotated[list[Path], ...]`.
                # But there might be still a better annotation in metadata `field: Annotated[list[Path], Tag(...)]`.
                field_type = _get_annotation_from_class_hierarchy(_src_class, _src_key)
                if field_type:
                    if hasattr(field_type, "__metadata__"):
                        for metadata in field_type.__metadata__:
                            if isinstance(metadata, Tag):  # NOTE might fetch from a pydantic model too
                                # The type of the Tag is another Tag
                                # Ex: `my_field: Validation(...) = 4`

                                new = copy(metadata)
                                new.val = val if val is not None else new.val
                                new.description = description or new.description
                                if new.annotation is None:
                                    # Annotated[ **origin** list[Path], Tag(...)]
                                    new.annotation = annotation or field_type.__origin__
                                # Annotated[date, Tag(name="hello")] = datetime.fromisoformat(...) -> DatetimeTag(date=True)
                                tag = tag_assure_type(new._fetch_from(Tag(*args, **kwargs), include_ref=True))
                            elif isinstance(metadata, (BaseMetadata, Len)):
                                # Why not checking `GroupedMetadata` instead of `Len`? See below. You won't believe.
                                validators.append(metadata)
                            elif get_origin(metadata) is Literal:
                                if "<class 'mininterface.tag.flag._Blank'>" in (repr(type(f)) for f in field_type.__metadata__):
                                    # a special case, this is a default CLI value and will be processed by flag.Blank
                                    # `foo: Annotated[Blank[int], Literal[2]] = None`
                                    # Using repr and not importing due to (vague) performance reasons.
                                    continue
                                # `variable = 2, 3; foo: Annotated[int, Literal[variable]] = None`
                                annotation = metadata
    if not tag:
        tag = tag_assure_type(Tag(val, description, annotation, *args, **kwargs))

    if validators:  # we prepend annotated_types validators to the current validator
        tag._add_validation(validators)
    return tag

# NOTE I'd like to check `GroupedMetadata` instead of the `Len` (the only currently supported GroupedMetadata).
# However, that's not possible because a mere checking of some things from the typing module,
# like `isinstance(Literal[2], GroupedMetadata)`, will add a trailing __annotations__ to some objects in the typing module.
#
# Once upon a day, I thought I debug a pretty obscure case from tyro, concerning global imports of a primitive specs registry
# when doing tests in paralel. The bug appeared reliably but only on the server, never on the localhost, and for Python3.12+
# only (which I am running to on localhost). I find out a test fails when another specific test is there. But it was not the end,
# the problem lied not in tyro but deeper, some chances are there is a bug in the Python itself. It turned out
# a mere presence of a Literal in an Annotated statement cause a bug in an independent test.
#
# The dark magic happens in typing._proto_hook at line
# `getattr(base, '__annotations__', {})`
# while `base = _LiteralSpecialForm)`
#
# This utterly obscure case will make tyro cycle when handling unions,
# Union must not have trailing __annotations__
# `runm([Subc1, Subc2])` # will cycle
# So the code breaks up a different time on another place. Tremendous.
#
# https://github.com/annotated-types/annotated-types/issues/94
#
# ```python
# from typing import Literal, Optional, Union
# from annotated_types import GroupedMetadata, Len
# print(hasattr(Union[1, 2],"__annotations__")) # False
# print(hasattr(Optional,"__annotations__")) # False
# print(hasattr(Literal,"__annotations__")) # False
#
# isinstance(Literal, GroupedMetadata)
#
# print(Union[1, 2].__annotations__) # {}
# print(Optional.__annotations__) # {}
# print(Literal.__annotations__) # {}
# ````
#