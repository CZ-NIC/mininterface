import warnings

from simple_term_menu import TerminalMenu

from ..tag.select_tag import SelectTag

from .._lib.auxiliary import flatten
from ..exceptions import Cancelled
from .._lib.form_dict import TagDict
from .._mininterface import Tag
from .._mininterface.adaptor import BackendAdaptor
from ..settings import TextSettings
from ..tag.internal import (BoolWidget, CallbackButtonWidget,
                            SubmitButtonWidget)
from ..tag.secret_tag import SecretTag
from .facet import TextFacet


class Submit(StopIteration):
    pass


class TextAdaptor(BackendAdaptor):

    facet: TextFacet
    settings: TextSettings

    def widgetize(self, tag: Tag, only_label=False):
        """ Represent Tag in a text form """

        if not only_label:
            label = tag.label
            if v := self.widgetize(tag, only_label=True):
                label += f" {v}"
            if d := tag.description:
                print(d)

        v = tag._get_ui_val()

        match tag:
            # NOTE: PathTag, DatetimeTag not implemented
            case SelectTag():
                options, values = zip(*((label + (" <--" if tip else " "), v)
                                        for label, v, tip, _ in tag._get_options(delim=" - ")))
                if tag.multiple:
                    if only_label:
                        return tag._get_selected_keys() or f"({len(options)} options)"
                    else:
                        return [values[i] for i in self._choose(options, title=tag.label, multiple=True)]
                else:
                    if only_label:
                        return tag._get_selected_key() or f"({len(options)} options)"
                    else:
                        return values[self._choose(options, title=tag.label)]
            case SecretTag():
                # NOTE the input should be masked (according to tag._masked)
                return tag._get_masked_val() if only_label else self.interface.ask(label)
            case _:
                match tag._recommend_widget():
                    case BoolWidget():
                        return ("✓" if v else "×") if only_label else self.interface.confirm(tag.label)
                    case SubmitButtonWidget():  # NOTE EXPERIMENTAL and not implemented here
                        if only_label:
                            return "(submit button)"
                        else:
                            tag.update(True)
                            tag._facet.submit()
                            raise Submit
                    case CallbackButtonWidget():  # Replace with a callback button
                        if only_label:
                            return "(submit)"
                        else:
                            tag._facet.submit(_post_submit=tag._run_callable)
                            raise Submit
                    case _:
                        if only_label:
                            return v
                        else:
                            return self.interface.ask(label, tag.annotation)

    def _get_tag_val(self, val: Tag | dict):
        match val:
            case Tag() as tag:
                s = f": {self.widgetize(tag, only_label=True) or '(empty)'}"
                if d := tag.description:
                    s = s + f" | {d}"
                    # sanitize chars that TerminalMenu does not handle well
                    return s.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                return s
            case dict() as d:
                return f"... ({len(d)}×)"

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """
        while True:
            try:
                try:
                    self._run_dialog(form, title, submit)
                except Submit:
                    pass
                if not Tag._submit_values((tag, tag.val) for tag in flatten(form)) or not self.submit_done():
                    continue
            except KeyboardInterrupt:
                raise Cancelled(".. cancelled")  # prevent being stuck in value type check
            break
        return form

    def _run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        super().run_dialog(form, title, submit)
        if title:
            self.facet.set_title(title)

        single = len(form) == 1
        while True:
            if single:
                key = next(iter(form))
            else:
                index = self._choose([f"{key}{self._get_tag_val(val)}" for key,
                                      val in form.items()], append_ok=True)
                key = list(form)[index]

            match form[key]:
                case dict() as submenu:
                    try:
                        self.run_dialog(submenu, key, submit)
                    except Cancelled:
                        if single:
                            raise
                case Tag() as tag:
                    while True:
                        try:
                            ui_val = self.widgetize(tag)
                        except KeyboardInterrupt:
                            if single:
                                raise Cancelled(".. cancelled")
                            print()
                            break
                        tag._on_change_trigger(ui_val)
                        if tag.update(ui_val):
                            break
                case _:
                    warnings.warn(f"Unsupported item {key}")
            if single:
                break
        return form

    def _choose(self, items: list, title=None, append_ok=False, multiple: bool = False) -> int | tuple[int]:
        it = items
        kwargs = {}
        if not multiple:
            if len(items) < 10:
                it = [f"[{i+1}] {item}" for i, item in enumerate(items)]
            else:
                kwargs = {"show_search_hint": True}

        if append_ok:
            it = ["ok"] + it
        while True:
            try:
                menu = TerminalMenu(it, title=title, multi_select=multiple, **kwargs)
                index = menu.show()
                break
            except ValueError:
                # library error
                # kwargs = {"show_search_hint": True, "search_key": None} + hitting left key raises this
                # https://github.com/IngoMeyer441/simple-term-menu/issues/41
                pass
        if index is None:
            raise Cancelled

        if multiple:
            index: tuple[int]
            if append_ok:
                if 0 in index:
                    raise Submit
                index = tuple(i-1 for i in index)
        else:
            index: int
            if append_ok:
                if index == 0:
                    raise Submit
                index -= 1
        return index
