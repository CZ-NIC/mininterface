""" Exceptions that might make sense to be used outside the library. """


class Cancelled(SystemExit):
    """ User has cancelled.
    A SystemExit based exception noting that the program exits without a traceback,
    ex. if user hits the escape or closes the window. """
    # We inherit from SystemExit so that the program exits without a traceback on ex. GUI escape.
    pass


class ValidationFail(ValueError):
    """ Signal to the form that submit failed and we want to restore it.
    """
    # NOTE example
    pass


class DependencyRequired(ImportError):
    def __init__(self, extras_name):
        super().__init__(extras_name)
        self.message = extras_name

    def __str__(self):
        return f"Required dependency. Run: pip install mininterface[{self.message}]"


class InterfaceNotAvailable(ImportError):
    """ Interface failed to init, ex. display not available in GUI. Or the underlying dependency was uninstalled. """
    pass
