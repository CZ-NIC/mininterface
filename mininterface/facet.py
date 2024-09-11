from abc import ABC, abstractmethod

from .form_dict import TagDict
from .tag import Tag


class Facet:
    """ A frontend side of the interface. While a dialog is open,
        this allows to set frontend properties like the heading. """
    # Every UI adopts this object through BackendAdaptor methods.
    # TODO

    def set_heading(self, text):
        pass


class BackendAdaptor(ABC):

    @staticmethod
    @abstractmethod
    def widgetize(tag: Tag):
        """ Wrap Tag to a textual widget. """
        pass

    @abstractmethod
    def run_dialog(self, form: TagDict, title: str = "") -> TagDict:
        """ Let the user edit the dict values. """
        pass
