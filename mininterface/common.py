class InterfaceNotAvailable(ImportError):
    pass


class Cancelled(SystemExit):
    """ User has cancelled. """
    # We inherit from SystemExit so that the program exits without a traceback on ex. GUI escape.
    pass