class HeadlessInterface:
    def run_dialog(self, *args, **kwargs):
        raise NotImplementedError

class ReplInterface(HeadlessInterface):
    def __getattr__(self, name):
        """ Run _HeadlessInterface method if exists and starts a REPL. """
        attr = getattr(super(), name, None)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                breakpoint()
                return result
            return wrapper
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")