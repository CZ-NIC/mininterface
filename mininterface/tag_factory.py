from copy import copy
from datetime import date, time
from enum import Enum
from pathlib import Path
from typing import Type, get_type_hints

from .tag import Tag
from .type_stubs import TagCallback
from .types import CallbackTag, DatetimeTag, PathTag, EnumTag


def _get_annotation_from_class_hierarchy(cls, key):
    for base in cls.__mro__:
        if key in getattr(base, '__annotations__', {}):
            return base.__annotations__[key]
    return None


def get_type_hint_from_class_hierarchy(cls, key):
    for base in cls.__mro__:
        hints = get_type_hints(base)
        if key in hints:
            return hints[key]
    return None


def _get_tag_type(tag: Tag) -> Type[Tag]:
    """ Return the most specific Tag child that a tag value can be expressed with.
        Ex. Return PathTag for a Tag having a Path as a value.
    """
    if tag._is_subclass(Path):
        return PathTag
    if tag._is_subclass(date) or tag._is_subclass(time):
        return DatetimeTag
    if tag._is_subclass(Enum):
        return EnumTag
    return type(tag)


def tag_fetch(tag: Tag, ref: dict | None, name: str):
    return tag._fetch_from(Tag(**ref), name)


def tag_assure_type(tag: Tag):
    """ morph to correct class `Tag("", annotation=Path)` -> `PathTag("", annotation=Path)` """
    if (type_ := _get_tag_type(tag)) is not Tag and not isinstance(tag, type_):
        # I cannot use type_._fetch_from(tag) here as EnumTag.__post_init__
        # needs the self.val which would not be yet set.
        return type_(**tag.__dict__)
    return tag


def tag_factory(val=None, description=None, annotation=None, *args, _src_obj=None, _src_key=None, _src_class=None, **kwargs):
    if _src_obj and not _src_class:
        # NOTE it seems _src_obj is sometimes accepts Type[DataClass], and not a DataClass,
        # unless I find out why, here is the workaround:
        if isinstance(_src_obj, type):  # form is a class, not an instance
            _src_class = _src_obj
        else:
            _src_class = _src_obj.__class__
    kwargs |= {"_src_obj": _src_obj, "_src_key": _src_key, "_src_class": _src_class}
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
                    if hasattr(field_type, '__metadata__'):
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
                                return tag_assure_type(new._fetch_from(Tag(*args, **kwargs)))
    return tag_assure_type(Tag(val, description, annotation, *args, **kwargs))
