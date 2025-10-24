"""Exceptions that might make sense to be used outside the library."""

from os import environ as _environ


class Cancelled(SystemExit):
    """User has cancelled.
    A SystemExit based exception noting that the program exits without a traceback,
    ex. if user hits the escape or closes the window."""

    # We inherit from SystemExit so that the program exits without a traceback on ex. GUI escape.
    pass


class ValidationFail(ValueError):
    """Signal to the form that submit failed and we want to restore it."""

    # NOTE example
    pass


class InterfaceNotAvailable(ImportError):
    """Interface failed to init, ex. display not available in GUI. Or an underlying dependency was uninstalled."""

    pass


class DependencyRequired(InterfaceNotAvailable):
    def __init__(self, extras_name):
        super().__init__(extras_name)
        self.message = extras_name

    def __str__(self):
        return f"Install the missing dependency by running: pip install mininterface[{self.message}]"

    def __call__(self, *args, **kwargs):
        """This is an elagant way to handling missing functions. Consider this case.

        ```python
        try:
            from .._lib.cli_parser import parse_cli
        except DependencyRequired as e:
            parse_cli = e
        ```

        When the function is used, the original exception is raised.
        """
        self.exit()

    def exit(self):
        """Wrap the exception in a SystemExit so that the program exits without a traceback."""
        _debug_wanted(self)
        raise SystemExit(self)


def _debug_wanted(e: Exception):
    # Undocumented MININTERFACE_DEBUG flag. Note ipdb package requirement.
    from ast import literal_eval

    if literal_eval(_environ.get("MININTERFACE_DEBUG", "0")):
        import traceback
        import ipdb

        traceback.print_exception(e)
        ipdb.post_mortem(e)
        return True
