from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, Optional


from .form_dict import EnvClass, TagDict
from .tag import Tag

if TYPE_CHECKING:
    from . import Mininterface


class BackendAdaptor(ABC):
    facet: "Facet"
    post_submit_action: Optional[Callable] = None

    @staticmethod
    @abstractmethod
    def widgetize(tag: Tag):
        """ Wrap Tag to a UI widget. """
        pass

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """ Let the user edit the dict values.

        Setups the facet._fetch_from_adaptor.
        """
        self.facet._fetch_from_adaptor(form)

    def submit_done(self):
        if self.post_submit_action:
            self.post_submit_action()


class MinAdaptor(BackendAdaptor):
    def __init__(self, interface: "Mininterface"):
        super().__init__()
        self.facet = Facet(self, interface.env)

    def widgetize(tag: Tag):
        pass

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        return form


class Facet(Generic[EnvClass]):
    """ A frontend side of the interface. While a dialog is open,
        this allows to set frontend properties like the heading.


    Read [`Tag.facet`][mininterface.Tag.facet] to see how to access from the front-end side.
    Read [`Mininterface.facet`][mininterface.Mininterface.facet] to see how to access from the back-end side.
    """
    # Every UI adopts this object through BackendAdaptor methods.

    _form: TagDict | None = None
    """ Experimental (apparently read-only) access to the current form. """
    _env: EnvClass | None = None
    """ Experimental access to the Mininterface.env.
    If you change something, it will not probably be shown in the form because there is no refresh mechanism.
    """

    def __init__(self, adaptor: BackendAdaptor, env: EnvClass):
        self.adaptor = adaptor
        self._env = env

    def _fetch_from_adaptor(self, form: TagDict):
        self._form = form

    def set_title(self, text):
        """ Set the main heading. """
        print("Title", text)

    def submit(self, _post_submit=None):
        """ Submits the whole form.

        ```python
        from mininterface import run, Tag

        def callback(tag: Tag):
            tag.facet.submit()

        m = run()
        out = m.form({
            "My choice": Tag(choices=["one", "two"], on_change=callback)
        })
        # continue here immediately after clicking on a radio button

        """
        self.adaptor.post_submit_action = _post_submit

    # NOTE we should get
    # Access to the fields. What is a catch,
    # if we change a value in the UI, their respective tag val is unchanged. Do we publish Tag values or UI values?
    # We would like to be able to refresh the Widget when update fails. However, facet does not allow method for that yet.
