from .tag import Tag
from .type_stubs import TagCallback
from .types import CallbackTag


from typing import get_type_hints


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
                                # Why fetching metadata name? The name would be taken from _src_obj.
                                # But the user defined in metadata is better.
                                return Tag(val, description, name=metadata.name, *args, **kwargs)._fetch_from(metadata)
    return Tag(val, description, annotation, *args, **kwargs)
