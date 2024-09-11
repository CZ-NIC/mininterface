import logging
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
if TYPE_CHECKING:  # remove the line as of Python3.11 and make `"Self" -> Self`
    from typing import Generic, Self
else:
    from typing import Generic

from .form_dict import EnvClass, FormDictOrEnv, dataclass_to_formdict, formdict_resolve

logger = logging.getLogger(__name__)


class Cancelled(SystemExit):
    # We inherit from SystemExit so that the program exits without a traceback on GUI Escape.
    pass


class Mininterface(Generic[EnvClass]):
    """ The base interface.
        You get one through [`mininterface.run`](run.md) which fills CLI arguments and config file to `mininterface.env`
        or you can create [one](.#all-possible-interfaces) directly (without benefiting from the CLI parsing).
    """
    # This base interface does not require any user input and hence is suitable for headless testing.

    def __init__(self, title: str = "",
                 _env: EnvClass | None = None,
                 _descriptions: dict | None = None,
                 ):
        self.title = title or "Mininterface"
        # Why `or SimpleNamespace()`?
        # We want to prevent error raised in `self.form(None)` if self.env would have been set to None.
        # It would be None if the user created this mininterface (without setting env)
        # or if __init__.run is used but Env is not a dataclass but a function (which means it has no attributes).
        self.env: EnvClass = _env or SimpleNamespace()
        """ Parsed arguments, fetched from cli
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
        self._descriptions = _descriptions or {}
        """ Field descriptions """

    def __enter__(self) -> "Self":
        """ When used in the with statement, the GUI window does not vanish between dialogs
            and it redirects the stdout to a text area. """
        return self

    def __exit__(self, *_):
        pass

    def alert(self, text: str) -> None:
        """ Prompt the user to confirm the text.  """
        print("Alert text", text)
        return

    def ask(self, text: str) -> str:
        """ Prompt the user to input a text.  """
        print("Asking", text)
        raise Cancelled(".. cancelled")

    def ask_number(self, text: str) -> int:
        """ Prompt the user to input a number. Empty input = 0. """
        print("Asking number", text)
        return 0

    def form(self, form: FormDictOrEnv | None = None, title: str = "") -> FormDictOrEnv | EnvClass:
        """ Prompt the user to fill up whole form.

        Args:
            form: Dict of `{labels: default value}`. The form widget infers from the default value type.
                The dict can be nested, it can contain a subgroup.
                The value might be a [`Tag`][mininterface.Tag] that allows you to add descriptions.
                If None, the `self.env` is being used as a form, allowing the user to edit whole configuration.
                    (Previously fetched from CLI and config file.)
                A checkbox example: `{"my label": Tag(True, "my description")}`
            title: Optional form title

        Returns:
            dict or dataclass:
                If the `form` is null, the output is [`self.env`][mininterface.Mininterface.env].

                If the `form` is a dict, the output is another dict.
                Whereas the original form stays intact (with the values update),
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
        # NOTE in the future, support form=arbitrary dataclass too
        if form is None:
            print(f"Asking the form {title}".strip(), self.env)
            return self.env
        f = form
        print(f"Asking the form {title}".strip(), f)
        return formdict_resolve(f, extract_main=True)

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
