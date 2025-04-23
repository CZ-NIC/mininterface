from ..exceptions import ValidationFail
from ..facet import Facet
from ..form_dict import TagDict
from ..settings import UiSettings
from ..tag import Tag


from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Literal, Optional

if TYPE_CHECKING:
    from . import Mininterface


class BackendAdaptor(ABC):
    """
    Connection point between a Mininterface and an external UI library.
    """
    facet: Facet
    post_submit_action: Optional[Callable] = None
    interface: "Mininterface"
    settings: UiSettings

    def __init__(self, interface: "Mininterface", settings: UiSettings | None):
        self.interface = interface
        self.facet = interface.facet = self.__annotations__["facet"](self, interface.env)
        self.settings = settings or self.__annotations__["settings"]()

    @abstractmethod
    def widgetize(self, tag: Tag):
        """ Wrap Tag to a UI widget. """
        pass

    @abstractmethod
    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """ Let the user edit the dict values.

        Setups the facet._fetch_from_adaptor.
        """
        self.facet._fetch_from_adaptor(form)

    def submit_done(self) -> bool:
        if self.post_submit_action:
            try:
                self.post_submit_action()
            except ValidationFail as e:
                # NOTE I'd prefer self.facet.set_title(str(e))
                # which is invisible in Subcommands
                if v := str(e):
                    self.interface.alert(v)
                return False
        return True


class MinAdaptor(BackendAdaptor):
    facet: Facet
    settings: UiSettings

    def widgetize(self, tag: Tag):
        pass

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        return form
