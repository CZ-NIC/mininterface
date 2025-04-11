from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any


from . import Mininterface


class ButtonMixin(Mininterface):
    _adaptor: "ButtonAdaptorMixin"

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self._adaptor.buttons(text, [("Ok", None)])

    def confirm(self, text, default: bool = True) -> bool:
        return self._adaptor.yes_no(text, not default)


class ButtonAdaptorMixin(ABC):
    @abstractmethod
    def yes_no(self, text: str, focus_no=True):
        ...

    @abstractmethod
    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        ...
