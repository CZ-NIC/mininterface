from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Type

from ..tag.tag_factory import assure_tag

from ..form_dict import DataClass, FormDict, EnvClass
from ..tag.tag import Tag, TagValue


from . import Mininterface


class RichUiMixin(Mininterface):
    _adaptor: "RichUiAdaptor"

    def alert(self, text: str) -> None:
        """ Display the OK dialog with text. """
        self._adaptor.buttons(text, [("Ok", None)])

    def confirm(self, text, default: bool = True) -> bool:
        return self._adaptor.yes_no(text, not default)

    def ask(self, text: str, annotation: Type[TagValue] | Tag = str) -> TagValue:
        return self.form({text: assure_tag(annotation)})[text]

    def form(self,
             form: DataClass | Type[DataClass] | FormDict | None = None,
             title: str = "",
             *,
             submit: str | bool = True
             ) -> FormDict | DataClass | EnvClass:
        return self._form(form, title, self._adaptor, submit=submit)


class RichUiAdaptor(ABC):
    @abstractmethod
    def yes_no(self, text: str, focus_no=True):
        ...

    @abstractmethod
    def buttons(self, text: str, buttons: list[tuple[str, Any]], focused: int = 1):
        ...
