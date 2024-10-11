from typing import Callable


class TagCallback(Callable):
    """ TODO docs submit button """
    pass


class TagType:
    """ TODO a mere Tag should work for a type too but Tyro interpretes it as a nested conf

    @dataclass
        class SpecificTime:
            date: str = ""  # Allow missing
            time: str = ""
            run: TagCallback = controller.specific_time
            run2: TagType = CallbackTag(controller.specific_time)

        m.form(SpecificTime())

    """
    pass
