from argparse import ArgumentParser
import logging
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from mininterface import EnvClass, Mininterface, Type, run
from mininterface._lib.form_dict import MissingTagValue, TagDict
from mininterface._mininterface import MinAdaptor

SYS_ARGV = None  # To be redirected

MISSING = MissingTagValue(BaseException(), None)

logger = logging.getLogger(__name__)

def runm(
    env_class: Type[EnvClass] | list[Type[EnvClass]] | ArgumentParser | None = None,
    args=None,
    **kwargs
) -> Mininterface[EnvClass]:
    logger.debug("Running %s with %s", env_class, args)
    return run(env_class, interface=Mininterface, args=args, **kwargs)


def mock_interactive_terminal(func):
    # mock the session could be made interactive
    @patch("sys.stdin.isatty", new=lambda: True)
    @patch("sys.stdout.isatty", new=lambda: True)
    @patch.dict(
        sys.modules, {"ipdb": None}
    )  # ipdb prevents vscode to finish test_ask_form
    def _(*args, **kwargs):
        return func(*args, **kwargs)

    return _


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
            for comp in (
                not_contains if isinstance(not_contains, list) else [not_contains]
            ):
                self.assertNotIn(comp, actual_output)

    def assertOutputs(
        self, expected_output=None, contains: str | list[str] = None, not_contains=None
    ):
        return self._assertRedirect(
            redirect_stdout, expected_output, contains, not_contains
        )

    def assertStderr(self, expected_output=None, contains=None, not_contains=None):
        return self._assertRedirect(
            redirect_stderr, expected_output, contains, not_contains
        )

    @contextmanager
    def assertForms(self, check: list[dict | None | tuple[dict | None, dict | None]]):
        """Intercepts every form call, checks it and possibly modify it (simulating the user input).

        Args:
            check: List of form calls. Form is represented by a tuple of model and setter (or just model). (If the list is shorter then the form call count, it's okay.)
                Model is compared to the form call.
                Values from setter are taken and injected into the form call, simulating the user input.
        """
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
            def run_dialog(
                self, form: TagDict, title: str = "", submit: bool | str = True
            ) -> TagDict:
                try:
                    model, setter = next(check_)
                    if model:
                        this.assertEqual(repr(form), repr(model))
                        logger.debug("Form passed %s", form)
                    else:
                        logger.debug("Form not checked %s", form)
                    if setter:
                        apply_setter(form, setter)

                except StopIteration:
                    # further form calls are without checks
                    pass
                except AssertionError:
                    logger.debug("Form failed %s", form)
                    raise

                # if not submit:
                #     submit = True # I should have the mechanism to choose the Tag to be submitted.

                return super().run_dialog(form, title, submit)

        class MockInterface(Mininterface[EnvClass]):
            _adaptor: MockAdaptor

        original_interface = Mininterface
        try:
            globals()["Mininterface"] = MockInterface
            yield
        finally:
            globals()["Mininterface"] = original_interface

    def assertReprEqual(self, a, b):
        return self.assertEqual(repr(a), repr(b))
