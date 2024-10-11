from .tag import Tag
from .type_stubs import TagCallback
from .types import CallbackTag


from typing import get_type_hints


def tag_factory(val=None, description=None, annotation=None, *args, _src_obj=None, _src_key=None, _src_class=None, **kwargs):
    if _src_obj and not _src_class:
        _src_class = _src_obj
    kwargs |= {"_src_obj": _src_obj, "_src_key": _src_key, "_src_class": _src_class}
    if _src_class:
        if not annotation:  # when we have _src_class, we assume to have _src_key too
            annotation = get_type_hints(_src_class).get(_src_key)
            if annotation is TagCallback:
                return CallbackTag(val, description, *args, **kwargs)
            else:
                field_type = _src_class.__annotations__.get(_src_key)
                if field_type and hasattr(field_type, '__metadata__'):
                    for metadata in field_type.__metadata__:
                        if isinstance(metadata, Tag):  # NOTE might fetch from a pydantic model too
                            # The type of the Tag is another Tag
                            # Ex: `my_field: Validation(...) = 4`
                            # Why fetching metadata name? The name would be taken from _src_obj.
                            # But the user defined in metadata is better.
                            return Tag(val, description, name=metadata.name, *args, **kwargs)._fetch_from(metadata)
    return Tag(val, description, annotation, *args, **kwargs)
