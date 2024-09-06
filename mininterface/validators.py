# Functions suitable for FormField validation.
from .FormField import FormField

def not_empty(ff: FormField):
    """ Assures that FormField the user has written a value and did not let the field empty.

    ```python
    from mininterface import FormField, validators

    m.form({"number", FormField("", validation=validators.not_empty)})
    # User cannot leave the string field empty.
    ```

    Note that for Path, an empty string is converted to an empty Path('.'),
    hence '.' too is considered as an empty input and the user
    is not able to set '.' as a value.
    This does not seem to me as a bad behaviour as in CLI you clearly see the CWD,
    whereas in a UI the CWD is not evident.
    """
    v = ff.val
    if v == "":
        return False
    elif v is False:
        return True
    try:
        return v != ff.annotation()
    except:
        pass
    return True
