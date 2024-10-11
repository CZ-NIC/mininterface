from enum import Enum
import logging
from dataclasses import is_dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload, Type

from .common import Cancelled
from .facet import Facet
from .form_dict import DataClass, EnvClass, FormDict, FormDictOrEnv, dict_to_tagdict, formdict_resolve
from .tag import ChoicesType, Tag, TagValue
from .form_dict import DataClass, FormDict, dataclass_to_tagdict, dict_to_tagdict, formdict_resolve
from .cli_parser import run_tyro_parser


if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Self

logger = logging.getLogger(__name__)


class Mininterface(Generic[EnvClass]):
    """ The base interface.
        You get one through [`mininterface.run`](run.md) which fills CLI arguments and config file to `mininterface.env`
        or you can create [one](Overview.md#all-possible-interfaces) directly (without benefiting from the CLI parsing).

    Raise:
        Cancelled: A SystemExit based exception noting that the program exits without a traceback, ex. if user hits the escape.

    Raise:
        InterfaceNotAvailable: Interface failed to init, ex. display not available in GUI.
    """
    # This base interface does not require any user input and hence is suitable for headless testing.

    def __init__(self, title: str = "",
                 _env: EnvClass | SimpleNamespace | None = None
                 ):
        self.title = title or "Mininterface"
        # Why `or SimpleNamespace()`?
        # We want to prevent error raised in `self.form(None)` if self.env would have been set to None.
        # It would be None if the user created this mininterface (without setting env)
        # or if __init__.run is used but Env is not a dataclass but a function (which means it has no attributes).
        # Why using EnvInstance? So that the docs looks nice, otherwise, there would be `_env or SimpleNamespace()`.
        EnvInstance = _env or SimpleNamespace()
        self.env: EnvClass = EnvInstance
        """ Parsed arguments, fetched from cli.
            Contains whole configuration (previously fetched from CLI and config file).

        ```bash
        $ program.py --number 10
        ```

        ```python
        from dataclasses import dataclass
        from mininterface import run

        @dataclass
        class Env:
            number: int = 3
            text: str = ""

        m = run(Env)
        print(m.env.number)  # 10
        ```

        """

        self.facet = Facet(None, self.env)
        """ Access to the UI [`facet`][mininterface.facet.Facet] from the back-end side.
        (Read [`Tag.facet`][mininterface.Tag.facet] to access from the front-end side.)

        ```python
        from mininterface import run
        with run(title='My window title') as m:
            m.facet.set_title("My form title")
            m.form({"My form": 1})
        ```

        ![Facet back-end](asset/facet_backend.avif)
        """

    def __enter__(self) -> "Self":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def alert(self, text: str) -> None:
        """ Prompt the user to confirm the text. """
        print("Alert text", text)
        return

    def ask(self, text: str) -> str:
        """ Prompt the user to input a text. """
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_number(self, text: str) -> int:
        """ Prompt the user to input a number. Empty input = 0.

        ```python
        m = run()  # receives a Mininterface object
        m.ask_number("What's your age?")
        ```

        ![Ask number dialog](asset/standalone_number.avif)

        Args:
            text: The question text.

        Returns:
            Number

        """
        print("Asking number", text)
        return 0

    def choice(self, choices: ChoicesType, title: str = "", _guesses=None,
               skippable: bool = True, launch: bool = True, _multiple=True, default: str | TagValue | None = None
               ) -> TagValue | list[TagValue] | Any:
        """ Prompt the user to select. Useful for a menu creation.

        Args:
            choices: You can denote the choices in many ways.
                Either put options in an iterable:

                ```python
                from mininterface import run
                m = run()
                m.choice([1, 2])
                ```

                ![Choices as a list](asset/choices_list.avif)

                Or to a dict `{name: value}`. Then name are used as labels.

                ```python
                m.choice({"one": 1, "two": 2})  # returns 1
                ```

                Alternatively, you may specify the names in [`Tags`][mininterface.Tag].

                ```python
                m.choice([Tag(1, name="one"), Tag(2, name="two")])  # returns 1
                ```

                ![Choices with labels](asset/choices_labels.avif)

                Alternatively, you may use an Enum.

                ```python
                class Color(Enum):
                    RED = "red"
                    GREEN = "green"
                    BLUE = "blue"

                m.choice(Color)
                ```

                ![Choices from enum](asset/choice_enum_type.avif)

                Alternatively, you may use an Enum instances list.

                ```python
                m.choice([Color.GREEN, Color.BLUE])
                ```

                ![Choices from enum list](asset/choice_enum_list.avif)

            title: Form title
            default: The value of the checked choice.

                ```python
                m.choice({"one": 1, "two": 2}, default=2)  # returns 2
                ```
                ![Default choice](asset/choices_default.avif)
            skippable: If there is a single option, choose it directly, without a dialog.
            launch: If the chosen value is a callback, we directly call it and return its return value.

        Returns:
            The chosen value.
            If launch=True and the chosen value is a callback, we call it and return its result.

        """
        # NOTE to build a nice menu, I need this
        # Args:
        # guesses: Choices to be highlighted.
        # multiple: Multiple choice.
        # Returns: If multiple=True, list of the chosen values.
        #
        # * Check: When inputing choices as Tags, make sure the original Tag.val changes too.
        #
        # NOTE UserWarning: GuiInterface: Cannot tackle the form, unknown winfo_manager .
        #   (possibly because the lambda hides a part of GUI)
        # m = run(Env)
        # tag = Tag(x, choices=["one", "two", x])
        if skippable and len(choices) == 1:
            if isinstance(choices, type) and issubclass(choices, Enum):
                out = list(choices)[0]
            elif isinstance(choices, dict):
                out = next(iter(choices.values()))
            else:
                out = choices[0]
            tag = Tag(out)
        else:
            tag = Tag(val=default, choices=choices)
            key = title or "Choose"
            self.form({key: tag})[key]

        if launch:
            if tag._is_a_callable():
                return tag._run_callable()
            if isinstance(tag.val, Tag) and tag.val._is_a_callable():
                # Nested Tag: `m.choice([CallbackTag(callback_tag)])` -> `Tag(val=CallbackTag)`
                return tag.val._run_callable()
        return tag.val

    @overload
    def form(self, form: None = None, title: str = "") -> EnvClass: ...
    @overload
    def form(self, form: FormDict, title: str = "") -> FormDict: ...
    @overload
    def form(self, form: Type[DataClass], title: str = "") -> DataClass: ...
    @overload
    def form(self, form: DataClass, title: str = "") -> DataClass: ...

    # NOTE: parameter submit_button = str (button text) or False to do not display the button
    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = ""
             ) -> FormDict | DataClass | EnvClass:
        """ Prompt the user to fill up an arbitrary form.

        Use scalars, enums, enum instances, objects like datetime, Paths or their list.

        ```python
        from enum import Enum
        from mininterface import run, Tag

        class Color(Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        m = run()
        out = m.form({
            "my_number": 1,
            "my_boolean": True,
            "my_enum": Color,
            "my_tagged": Tag("", name='Tagged value', description='Long hint'),
            "my_path": Path("/tmp"),
            "my_paths": [Path("/tmp")],
            "My enum with default": Color.BLUE
        })
        ```

        ![Complex form dict](asset/complex_form_dict.avif)

        Args:
            form: Dict of `{labels: value}`. The form widget infers from the default value type.
                The dict can be nested, it can contain a subgroup.
                The value might be a [`Tag`][mininterface.Tag] that allows you to add descriptions.
                If None, the `self.env` is being used as a form, allowing the user to edit whole configuration.
                    (Previously fetched from CLI and config file.)
                A checkbox example: `{"my label": Tag(True, "my description")}`
            title: Optional form title

        Returns:
            dataclass:
                If the `form` is null, the output is [`self.env`][mininterface.Mininterface.env].
            dict:
                If the `form` is a dict, the output is another dict.

                Whereas the original dict stays intact (with the values updated),
                we return a new raw dict with all values resolved
                (all [`Tag`][mininterface.Tag] objects are resolved to their value).

                ```python
                original = {"my label": Tag(True, "my description")}
                output = m.form(original)  # Sets the label to False in the dialog

                # Original dict was updated
                print(original["my label"])  # Tag(False, "my description")

                # Output dict is resolved, contains only raw values
                print(output["my label"])  # False
                ```

                ---
                Why this behaviour? You need to do some validation, hence you put
                `Tag` objects in the input dict. Then, you just need to work with the values.

                ```python
                original = {"my label": Tag(True, "my description")}
                output = m.form(original)  # Sets the label to False in the dialog
                output["my_label"]
                ```

                In the case you are willing to re-use the dict, you need not to lose the definitions,
                hence you end up with accessing via the `.val`.

                ```python
                original = {"my label": Tag(True, "my description")}

                for i in range(10):
                    m.form(original, f"Attempt {i}")
                    print("The result", original["my label"].val)
                ```
        """
        print(f"Asking the form {title}".strip(), self.env if form is None else form)
        return self._form(form, title, lambda tag_dict, title=None: tag_dict)

    def _form(self,
              form: DataClass | Type[DataClass] | FormDict | None = None,
              title: str = "",
              launch_callback=None) -> FormDict | DataClass | EnvClass:
        _form = self.env if form is None else form
        if isinstance(_form, dict):
            # TODO integrate to TextualMininterface and others, test and docs
            # TODO After launching a callback, a TextualInterface stays, the form re-appears.
            return formdict_resolve(launch_callback(dict_to_tagdict(_form, self.facet), title=title), extract_main=True)
        if isinstance(_form, type):  # form is a class, not an instance
            _form, wf = run_tyro_parser(_form, {}, False, False, args=[])  # TODO what to do with wf
        if is_dataclass(_form):  # -> dataclass or its instance
            # the original dataclass is updated, hence we do not need to catch the output from launch_callback
            launch_callback(dataclass_to_tagdict(_form, self.facet))
            return _form
        raise ValueError(f"Unknown form input {_form}")

    def is_yes(self, text: str) -> bool:
        """ Display confirm box, focusing yes.

        ```python
        m = run()
        print(m.is_yes("Is that alright?"))  # True/False
        ```

        ![Is yes window](asset/is_yes.avif "A prompted dialog")
        """
        print("Asking yes:", text)
        return True

    def is_no(self, text: str) -> bool:
        """ Display confirm box, focusing no. """
        print("Asking no:", text)
        return False
