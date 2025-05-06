from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Type
from warnings import warn

from .tag import Tag, TagValue

OptionsReturnType = list[tuple[str, TagValue, bool, tuple[str]]]
OptionLabel = str
RichOptionLabel = OptionLabel | tuple[OptionLabel]
OptionsType = (list[TagValue] | tuple[TagValue, ...] | set[TagValue]
               | dict[RichOptionLabel, TagValue] | Iterable[Enum] | Type[Enum])
""" You can denote the options in many ways.
Either put options in an iterable or to a dict `{labels: value}`.
Values might be Tags as well. Let's take a detailed look. We will use the [`run.select(OptionsType)`][mininterface.Mininterface.select] to illustrate the examples.

## Iterables like list

Either put options in an iterable:

```python
from mininterface import run
m = run()
m.select([1, 2])
```

![Options as a list](asset/choices_list.avif)

## Dict for labels

Or to a dict `{name: value}`. Then name are used as labels.

```python
m.select({"one": 1, "two": 2})  # returns 1
```

## Dict with tuples for table

If you use tuple as the keys, they will be joined into a table.

```python
m.select({("one", "two", "three"): 1, ("lorem", "ipsum", "dolor") : 2})
```

![Table like](asset/choice_table_span.avif)

## Tags for labels

Alternatively, you may specify the names in [`Tags`][mininterface.Tag].

```python
m.select([Tag(1, name="one"), Tag(2, name="two")])  # returns 1
```

![Options with labels](asset/choices_labels.avif)

## Enums

Alternatively, you may use an Enum.

```python
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

m.select(Color)
```

![Options from enum](asset/choice_enum_type.avif)

Alternatively, you may use an Enum instance. (Which means the default value is already selected.)

```python
class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

m.select(Color.BLUE)
```

![Options from enum](asset/choice_enum_instance.avif)

Alternatively, you may use an Enum instances list.

```python
m.select([Color.GREEN, Color.BLUE])
```

![Options from enum list](asset/choice_enum_list.avif)

## Further examples

See [mininterface.select][mininterface.Mininterface.select] or [`SelectTag.options`][mininterface.tag.SelectTag.options] for further usage.
"""


@dataclass(repr=False)
class SelectTag(Tag[TagValue]):
    """ Handle options – radio buttons / select box.
    The value serves as the initially selected choice.
    It is constrained to those defined in the `options` attribute.
    """

    options: OptionsType | None = None
    """ The possible values.


    ```python
    m.form({"My restrained": SelectTag(options=("one", "two"))})
    ```

    You can denote the options in many ways. Either put options in an iterable, or to a dict with keys as a values. You can also you tuples for keys to get a table-like formatting. Use the Enums or nested Tags... See the [`OptionsType`][mininterface.tag.select_tag.OptionsType] for more details.

    Here we focus at the `SelectTag` itself and its [`Options`][mininterface.tag.alias.Options] alias. It can be used to annotate a default value in a dataclass.

    ```python
    from dataclasses import dataclass
    from typing import Annotated
    from mininterface import run, Options
    from mininterface.tag import SelectTag

    @dataclass
    class Env:
        foo: Annotated["str", Options("one", "two")] = "one"
        # `Options` is an alias for `SelectTag(options=)`
        #   so the same would be:
        # foo: Annotated["str", SelectTag(options=("one", "two"))] = "one"

    m = run(Env)
    m.form()  # prompts a dialog
    ```
    ![Form choice](asset/tag_choices.avif)

    !!! Tip
        When dealing with a simple use case, use the [mininterface.select][mininterface.Mininterface.select] dialog.
    """
    # NOTE we should support (maybe it is done)
    # * Enums: Tag(enum) # no `choice` param`
    # * more date types (now only str possible)
    # * mininterface.select `def choice(options=, guesses=)`

    multiple: Optional[bool] = None

    tips: OptionsType | None = None

    def __repr__(self):
        return super().__repr__()[:-1] + f", options={[k for k, *_ in self._get_options()]})"

    def __post_init__(self):
        # Determine multiple
        candidate = self.val
        if isinstance(self.val, list):
            if self.multiple is False:
                raise ValueError("Multiple cannot be set to False when value is a list")
            self.multiple = True
            if len(self.val):
                candidate = self.val[0]
        elif self.val is not None:
            if self.multiple:
                raise ValueError("Multiple cannot be set to True when value is not a list")
            self.multiple = False

        # Disabling annotation is not a nice workaround, but it is needed for the `super().update` to be processed
        self.annotation = type(self)
        reset_name = not self.label
        super().__post_init__()
        if reset_name:
            # Inheriting the name of the default value in self.val (done in post_init)
            # does not make sense to me. Let's reset here so that we receive
            # the dict key or the dataclass attribute name as the name in form_dict.py .
            self.label = None
        self.annotation = None

        # Assure list val for multiple selection
        if self.val is None and self.multiple:
            self.val = []

        # Determine options
        if not self.options:
            if isinstance(candidate, Enum):  # Enum instance, ex: val=ColorEnum.RED
                self.options = candidate.__class__
            elif isinstance(candidate, type) and issubclass(candidate, Enum):  # Enum type, ex: val=ColorEnum
                self.options = self.val
                self.val = None

    def __hash__(self):  # every Tag child must have its own hash method to be used in Annotated
        return super().__hash__()

    @classmethod
    def _get_tag_val(cls, v) -> TagValue:
        """ TagValue can be anything, except the Tag. The nested Tag returns its value instead. """
        if isinstance(v, Tag):
            return cls._get_tag_val(v.val)
        return v

    def _get_selected_key(self):
        if self.multiple:
            raise AttributeError
        for k, val, *_ in self._get_options():
            if val is self.val:
                return k
        return None

    def _get_selected_keys(self):
        if not self.multiple:
            raise AttributeError
        return [k for k, val, *_ in self._get_options() if val in self.val]

    @classmethod
    def _repr_val(cls, v):
        if cls._is_a_callable_val(v):
            return v.__name__
        if isinstance(v, Tag):
            return v._get_name(True)
        if isinstance(v, Enum):  # enum instances collection, ex: list(ColorEnum.RED, ColorEnum.BLUE)
            return str(v.value)
        return str(v)

    def _build_options(self) -> dict[OptionLabel, TagValue]:
        """ Whereas self.options might have different format, this returns a canonic dict. """

        if self.options is None:
            return {}
        if isinstance(self.options, dict):
            # assure the key is a str or their tuple
            return {(tuple(str(k) for k in key) if isinstance(key, tuple) else str(key)): self._get_tag_val(v)
                    for key, v in self.options.items()}
        if isinstance(self.options, Iterable):
            return {self._repr_val(v): self._get_tag_val(v) for v in self.options}
        if isinstance(self.options, type) and issubclass(self.options, Enum):  # Enum type, ex: options=ColorEnum
            return {str(v.value): self._get_tag_val(v) for v in list(self.options)}

        warn(f"Not implemented options: {self.options}")

    def _get_options(self, delim=" - ") -> OptionsReturnType:
        """ Return a list of tuples (label, choice value, is tip, tupled-label).

        User has the possibility to write tuples instead of labels. We should produce a table then.
        In label, we are sure the keys are strings (possibly joined with a dash)
        but some interfaces (Tk) want to do the keys into the table processing on their own.
        So they use tupled-label when they are guaranteed to find a tuple.

        The interface should display label or tupled-label, hightlight options with is tip
        and keep the choice value invisible under the hood. When the user makes the choice,
        call tag.update() with the invisible choice value.

        Args:
            delim: Delimit the 1th argument with the chars. (If label are tuples.)
        """

        index = set(self.tips or tuple())
        front = []
        back = []

        options = self._build_options()

        keys = options.keys()
        labels: Iterable[tuple[str, tuple[str]]]
        """ First is the str-label, second is guaranteed to be a tupled label"""

        if len(options) and isinstance(next(iter(options)), tuple):
            labels = self._span_to_lengths(keys, delim)
        else:
            labels = ((key, (key,)) for key in keys)

        for (label, tupled), v in zip(labels, options.values()):
            tupled: tuple[str]
            if v in index:
                front.append((label, v, True, tupled))
            else:
                back.append((label, v, False, tupled))
        return front + back

    def _span_to_lengths(self, keys: Iterable[tuple[str]], delim=" - "):
        """ Span key tuple into a table
        Ex: [ ("one", "two"), ("hello", "world") ]
            one   - two
            hello - world"
        """
        a_key = next(iter(keys))
        try:
            col_widths = [max(len(row[i]) for row in keys) for i in range(len(a_key))]
            return [(delim.join(cell.ljust(col_widths[i]) for i, cell in enumerate(key)), key) for key in keys]
        except IndexError:
            # different lengths, table does not work
            # Ex: [ ("one", "two", "three"), ("hello", "world") ]
            return [(delim.join(key), key) for key in keys]

    def update(self, ui_value: TagValue | list[TagValue]) -> bool:
        """ ui_value is one of the self.options values  """
        ch = self._build_options()

        if self.multiple:
            vals = set(ch.values())
            if not all(v in vals for v in ui_value):
                self.set_error_text(f"Must be one of {list(ch.keys())}")
                return False
            return super().update(ui_value)
        else:
            if ui_value in ch.values():
                return super().update(ui_value)
            else:
                self.set_error_text(f"Must be one of {list(ch.keys())}")
                return False

    def _validate(self, out_value):
        vals = self._build_options().values()

        if self.multiple:
            if all(v in vals for v in out_value):
                return out_value
            else:
                self.set_error_text(f"A value is not one of the allowed")
                raise ValueError
        else:
            if out_value in vals:
                return out_value
            else:
                self.set_error_text(f"Not one of the allowed values")
                raise ValueError
