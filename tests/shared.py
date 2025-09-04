from argparse import ArgumentParser
from ast import literal_eval
import logging
from os import environ
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from mininterface import EnvClass, Mininterface, Type, run
from mininterface._lib.auxiliary import dict_diff
from mininterface._lib.form_dict import MissingTagValue, TagDict, dict_has_main, dict_removed_main, tagdict_resolve, dict_added_main
from mininterface._mininterface import MinAdaptor

SYS_ARGV = None  # To be redirected

MISSING = MissingTagValue()

logger = logging.getLogger(__name__)


def runm(
    env_class: Type[EnvClass] | list[Type[EnvClass]] | ArgumentParser | None = None, args=None, **kwargs
) -> Mininterface[EnvClass]:
    logger.debug("Running %s with %s", env_class, args)
    return run(env_class, interface=Mininterface, args=args, **kwargs)


def mock_interactive_terminal(func):
    # mock the session could be made interactive
    @patch("sys.stdin.isatty", new=lambda: True)
    @patch("sys.stdout.isatty", new=lambda: True)
    @patch.dict(sys.modules, {"ipdb": None})  # ipdb prevents vscode to finish test_ask_form
    def _(*args, **kwargs):
        return func(*args, **kwargs)

    return _


def _repr_dict(data: dict):
    """Return a string representation of a dictionary, converting types to their names
    without quotes, and using standard repr for other values.

    >>> repr_dict({'Choose': test_subcommands.Subc1})
    "{'Choose': Subc1}"
    """

    def _repr(v):
        if isinstance(v, dict):
            items = ", ".join(f"'{k}': {_repr(val)}" for k, val in v.items())
            return f"{{{items}}}"
        elif isinstance(v, type):
            return v.__name__
        elif hasattr(v, "__origin__"):
            return v.__origin__.__name__ if hasattr(v.__origin__, "__name__") else str(v.__origin__).split(".")[-1]
        else:
            return repr(v)

    return _repr(data)


class TestAbstract(TestCase):
    def setUp(self):
        global SYS_ARGV
        SYS_ARGV = sys.argv
        self.sys()

    def tearDown(self):
        global SYS_ARGV
        sys.argv = SYS_ARGV

    @classmethod
    def sys(cls, *args):
        sys.argv = ["running-tests", *args]

    @contextmanager
    def _assertRedirect(
        self,
        redirect,
        expected_output=None,
        contains: str | list[str] = None,
        not_contains: str | list[str] = None,
    ):
        f = StringIO()
        with redirect(f):
            yield
        actual_output = f.getvalue().strip()
        if expected_output is not None:
            self.assertEqual(expected_output, actual_output)
        if contains is not None:
            for comp in contains if isinstance(contains, list) else [contains]:
                self.assertIn(comp, actual_output)
        if not_contains is not None:
            for comp in not_contains if isinstance(not_contains, list) else [not_contains]:
                self.assertNotIn(comp, actual_output)

    def assertOutputs(self, expected_output=None, contains: str | list[str] = None, not_contains=None):
        return self._assertRedirect(redirect_stdout, expected_output, contains, not_contains)

    def assertStderr(self, expected_output=None, contains=None, not_contains=None):
        return self._assertRedirect(redirect_stderr, expected_output, contains, not_contains)

    @contextmanager
    def assertForms(self, *check: dict | None | tuple[dict | None, dict | None], end=True, wizzard=False):
        """Intercepts every form call, checks it and possibly modify it (simulating the user input).

        Args:
            check: Form calls. Form is represented by a tuple of model and setter (or just model).
                The length of checks must match the form call count (unless changed by `end`).
                Model is compared to the form call.
                Values from setter are taken and injected into the form call, simulating the user input.
            end: If True, the list must match whole form call count.
            wizzard: Interactively build a unit test. Raises forms and output the test parameters – the models and changed setters.
                You can use an undocumented MININTERFACE_WIZZARD env variable.
                Ex. MININTERFACE_WIZZARD=1 pytest -s test_...

                How to use it?
                1. Make a test stub
                    ```
                    def test_stub(self):
                        with self.assertForms():
                            runm([Subc1, Subc2])
                    ```

                2. Run `MININTERFACE_WIZZARD=1 pytest -s tests/test_...::test_stub`
                3. Do whatever in the GUI.
                4. Your passage is recorded to the clipboard. Just paste it into the test stub.
        """
        # Prepare wizzard
        builder = []
        if literal_eval(environ.get("MININTERFACE_WIZZARD", "0")):
            wizzard = True
        if wizzard:
            logging.basicConfig(level=logging.DEBUG, force=True)
            mint = run()

        # normalize - assure items are tuples
        check_ = iter(it if isinstance(it, tuple) else (it, None) for it in check)
        this = self
        logger.debug("Intercepting %d form calls...", len(check))

        def apply_setter(form, setter: dict):
            for k, v in setter.items():
                if isinstance(v, dict):
                    apply_setter(form[k], v)
                else:
                    form[k].val = v

        class MockAdaptor(MinAdaptor):
            def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
                if wizzard:
                    origr = repr(form).replace(", annotation=typing.", ", annotation=")  # typing.Optional -> Optional
                    main = dict_has_main(form)
                    out = dict_diff(tagdict_resolve(form), dict_added_main(mint.form(form)))
                    if not main:
                        out = dict_removed_main(out)
                    builder.append((origr, _repr_dict(out)))
                else:
                    try:
                        model, setter = next(check_)
                        if model:
                            this.assertEqual(repr(form), repr(model))
                            logger.debug("Form passed %s", form)
                        else:
                            logger.debug("Form not checked %s", form)
                        if setter:
                            try:
                                apply_setter(form, setter)
                            except KeyError:
                                raise ValueError(f"Setter failed: {setter}")

                    except StopIteration:
                        if end:
                            raise StopIteration(f"There is another form call: {form}")
                        pass  # further form calls are without checks
                    except AssertionError:
                        logger.debug("Form failed %s", form)
                        raise

                # if not submit:
                #     submit = True # I should have the mechanism to choose the Tag to be submitted.

                return super().run_dialog(form, title, submit)

        class MockInterface(Mininterface[EnvClass]):
            _adaptor: MockAdaptor

        original_interface = Mininterface
        had_exception = False
        try:
            globals()["Mininterface"] = MockInterface
            try:
                yield
            except:
                had_exception = True
                raise
        finally:
            globals()["Mininterface"] = original_interface

            if wizzard:
                # print("with self.assertForms(")
                # rows = [(f"    (\n      {a},\n      {b}\n    )") for a,b in builder]
                # print(",\n    ".join(rows))
                # print("  ):")

                s = "with self.assertForms(\n"
                rows = [f"    (\n      {a},\n      {b}\n    )" for a, b in builder]
                s += ",\n    ".join(rows)
                s += "\n  ):"
                try:
                    import pyperclip

                    pyperclip.copy(s)
                    print("Copied into clipboard!")
                except ImportError:
                    pass
                print(s)
            elif not had_exception:
                try:
                    model, setter = next(check_)
                    raise ValueError(f"Form not raised: {model}")
                except StopIteration:
                    pass

    def assertReprEqual(self, a, b):
        return self.assertEqual(repr(a), repr(b))
