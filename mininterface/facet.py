from abc import ABC, abstractmethod

from .form_dict import TagDict
from .tag import Tag


class BackendAdaptor(ABC):
    facet: "Facet"

    @staticmethod
    @abstractmethod
    def widgetize(tag: Tag):
        """ Wrap Tag to a textual widget. """
        pass

    @abstractmethod
    def run_dialog(self, form: TagDict, title: str = "") -> TagDict:
        """ Let the user edit the dict values. """
        pass


class Facet:
    """ A frontend side of the interface. While a dialog is open,
        this allows to set frontend properties like the heading.


    Read [`Tag.facet`][mininterface.Tag.facet] to see how to access from the front-end side.
    Read [`Mininterface.facet`][mininterface.Mininterface.facet] to see how to access from the back-end side.
    """
    # Every UI adopts this object through BackendAdaptor methods.

    @abstractmethod
    def __init__(self, window: BackendAdaptor):
        ...

    @abstractmethod
    def set_title(self, text):
        """ Set the main heading. """
        ...

    # @abstractmethod
    # def submit(self, text):
    #     """ Submits the whole form """
    #   (ex for checkbox on_change)
    #     raise NotImplementedError  # NOTE
    #
    # Access to the fields.


class MinFacet(Facet):
    """ A mininterface needs a facet and the base Facet is abstract and cannot be instanciated. """

    def __init__(self, window=None):
        pass
