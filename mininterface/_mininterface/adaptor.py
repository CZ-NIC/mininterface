from abc import ABC, abstractmethod
from itertools import chain
from string import ascii_lowercase
from typing import TYPE_CHECKING, Callable, Optional

from .._lib.auxiliary import flatten
from ..exceptions import Cancelled, ValidationFail
from ..facet import Facet
from .._lib.form_dict import TagDict
from ..settings import UiSettings
from ..tag.tag import Tag, ValsType, MissingTagValue

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
        if self.settings.mnemonic is not False:
            self._determine_mnemonic(form, self.settings.mnemonic is True)

    def _determine_mnemonic(self, form: TagDict, also_nones=False):
        """ also_nones – Also determine those tags when Tag.mnemonic=None. """
        # Determine mnemonic
        used_mnemonic = set()
        to_be_determined: list[Tag] = []
        tags = list(flatten(form))
        if len(tags) <= 1:  # do not use mnemonic for single field which is focused by default
            return
        for tag in tags:
            if tag.mnemonic is False:
                continue
            if isinstance(tag.mnemonic, str):
                used_mnemonic.add(tag.mnemonic)
                tag._mnemonic = tag.mnemonic
            elif also_nones or tag.mnemonic:
                # .settings.mnemonic=None + tag.mnemonic=True OR
                # .settings.mnemonic=True + tag.mnemonic=None
                to_be_determined.append(tag)

        # Find free mnemonic for Tag
        for tag in to_be_determined:
            # try every char in label
            # then, if no free letter, give a random letter
            for c in chain((c.lower() for c in tag.label if c.isalpha()), ascii_lowercase):
                if c not in used_mnemonic:
                    used_mnemonic.add(c)
                    tag._mnemonic = c
                    break

    def submit_done(self) -> bool:
        if action := self.post_submit_action:
            # Here, we prevent recursion:
            #
            # @dataclass
            # class Ask(Command):
            #     def run(self):
            #         self._facet.adaptor.interface.ask(self.label)
            self.post_submit_action = None
            try:
                action()
            except ValidationFail as e:
                # NOTE I'd prefer self.facet.set_title(str(e))
                # which is invisible in Subcommands
                if v := str(e):
                    self.interface.alert(v)
                return False
            finally:
                self.post_submit_action = action
        return True

    def _try_submit(self, vals: ValsType):
        return Tag._submit_values(vals) and self.submit_done()

    def _destroy(self):
        """ This interface will not be used any more.
        This is due to TkInterface tkinter window:
        1. Create one interface
        2. Create second without destroying the first
        3. The first is still the default window.
        4. Hence all variables somehow exist in the first
        and all the forms are empty.

        Note this is not documented as it is not used.

        It still does no handle the case when two interfaces co-exist together.
        We should be able to not use the default master but to register to the current one.
        Then, this method would not be used anymore.
        """
        ...


class MinAdaptor(BackendAdaptor):
    facet: Facet
    settings: UiSettings

    def widgetize(self, tag: Tag):
        pass

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str | Tag = True) -> TagDict:
        if not submit:
            raise Cancelled("Do not know what to submit")
        elif isinstance(submit, Tag):
            # NOTE this functionality exists for handling the test cases... And it not yet used.
            self.facet.submit(_post_submit=submit._run_callable)

        tags = list(flatten(form))
        if not self._try_submit((tag, tag.val) for tag in tags):
            tyro_error = ""
            # I think the eavesdrop is always the same text but to be sure, join them
            eavesdrop = set(tag.val.eavesdrop for tag in tags if isinstance(tag.val, MissingTagValue))
            if eavesdrop:
                tyro_error = "\n" + "\n".join(s for s in eavesdrop)

            validation_fails = "\n".join(f"{tag._original_label}: {tag._error_text}"
                                         for tag in tags if tag._error_text)

            raise SystemExit(validation_fails + tyro_error)

        return form
