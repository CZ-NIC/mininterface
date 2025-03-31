import warnings

from simple_term_menu import TerminalMenu

from ..exceptions import Cancelled
from ..form_dict import TagDict
from ..mininterface import Tag
from ..mininterface.adaptor import BackendAdaptor
from ..options import TextOptions
from ..types.internal import (BoolWidget, CallbackButtonWidget,
                              SubmitButtonWidget)
from ..types.rich_tags import EnumTag, SecretTag
from .facet import TextFacet


class Submit(StopIteration):
    pass


class TextAdaptor(BackendAdaptor):

    facet: TextFacet
    options: TextOptions

    def widgetize(self, tag: Tag, only_label=False):
        """ Represent Tag in a text form """
        # NOTE some field does not return description

        if not only_label:
            label = tag.name
            if v := self.widgetize(tag, only_label=True):
                label += f" {v}"
            if d := tag.description:
                print(d)

        v = tag._get_ui_val()

        match tag._recommend_widget():
            # NOTE: PathTag, DatetimeTag not implemented
            case BoolWidget():
                return ("✓" if v else "×") if only_label else self.interface.is_yes(tag.name)
            case EnumTag():
                choices = tag._get_choices()
                if only_label:
                    return tag.val or f"({len(choices)} options)"
                else:
                    return list(choices)[self._choose(choices, title=tag.name)]
            case SecretTag():
                # NOTE the input should be masked (according to tag._masked)
                return tag._get_masked_val() if only_label else self.interface.ask(label)
            case SubmitButtonWidget():  # NOTE EXPERIMENTAL and not implemented here
                if only_label:
                    return "(submit button)"
                else:
                    tag.update(True)
                    tag.facet.submit()
                    raise Submit
            case CallbackButtonWidget():  # Replace with a callback button
                if only_label:
                    return "(submit)"
                else:
                    tag.facet.submit(_post_submit=tag._run_callable)
                    raise Submit
            case _:
                if only_label:
                    return v
                elif tag._is_subclass((int, float)):
                    return self.interface.ask_number(label)
                else:
                    return self.interface.ask(label)

    def _get_tag_val(self, val: Tag | dict):
        match val:
            case Tag() as tag:
                s = f": {self.widgetize(tag, only_label=True) or '(empty)'}"
                if d := tag.description:
                    return s + f" \\| {d}"
                return s
            case dict() as d:
                return f"... ({len(d)}×)"

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """ Let the user edit the form_dict values in a GUI window.
        On abrupt window close, the program exits.
        """
        while True:
            try:
                self._run_dialog(form, title, submit)
            except Submit:
                pass
            if not self.submit_done():
                continue
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
                try:
                    index = self._choose([f"{key}{self._get_tag_val(val)}" for key,
                                         val in form.items()], append_ok=True)
                except Cancelled:
                    break
                key = list(form)[index]
            match form[key]:
                case dict() as submenu:
                    try:
                        self._run_dialog(submenu, key, submit)
                    except (KeyboardInterrupt, Cancelled):
                        continue
                case Tag() as tag:
                    while True:
                        try:
                            if tag.update(self.widgetize(tag)):
                                break
                        except KeyboardInterrupt:
                            print()
                            break
                case _:
                    warnings.warn(f"Unsupported item {key}")
            if single:
                break
        return form

    def _choose(self, items: list, title=None, append_ok=False) -> int:
        it = items
        if len(items) < 10:
            it = [f"[{i+1}] {item}" for i, item in enumerate(items)]
            kwargs = {}
        else:
            kwargs = {"show_search_hint": True}

        if append_ok:
            it = ["ok"] + it
        while True:
            try:
                menu = TerminalMenu(it, title=title, **kwargs)
                index = menu.show()
                break
            except ValueError:
                # library error
                # kwargs = {"show_search_hint": True, "search_key": None} + hitting left key raises this
                # https://github.com/IngoMeyer441/simple-term-menu/issues/41
                pass
        if index is None:
            raise Cancelled
        if append_ok:
            if index == 0:
                raise Cancelled
            index -= 1
        return index
