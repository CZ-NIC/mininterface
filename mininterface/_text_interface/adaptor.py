import re
import warnings

try:
    # Does not work on Windows (needs termios), we fall back to a plain input() menu then.
    # https://github.com/IngoMeyer441/simple-term-menu/issues/5
    from simple_term_menu import TerminalMenu
except ImportError:
    TerminalMenu = None

from .._lib.auxiliary import flatten
from .._lib.form_dict import TagDict
from .._mininterface import Tag
from .._mininterface.adaptor import BackendAdaptor
from ..exceptions import Cancelled
from ..settings import TextSettings
from ..tag.internal import BoolWidget, CallbackButtonWidget, SubmitButtonWidget
from ..tag.secret_tag import SecretTag
from ..tag.select_tag import SelectTag
from .facet import TextFacet
from .timeout import input_timeout


class Submit(StopIteration):
    pass


class TextAdaptor(BackendAdaptor):

    facet: TextFacet
    settings: TextSettings

    _plain_menu_fallback = False
    """ TerminalMenu is importable but refused to run (no real terminal); stick to the plain menu. """

    def widgetize(self, tag: Tag, only_label=False):
        """Represent Tag in a text form"""

        if not only_label:
            label = tag.label
            if v := self.widgetize(tag, only_label=True):
                label = f"{label} {v}" if label else str(v)
            if d := tag.description:
                print(d)

        v = tag._get_ui_val()

        match tag:
            # NOTE: PathTag, DatetimeTag not implemented
            case SelectTag():
                options, values = zip(
                    *((label + (" <--" if tip else " "), v) for label, v, tip, _ in tag._get_options(delim=" - "))
                )
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
                    s = f"{s} | {d}"
                # newlines would break the single-line menu entry in either menu;
                # the literal '|' is escaped for TerminalMenu later, in _choose_menu
                return s.replace("\n", " ").replace("\r", " ")
            case dict() as d:
                return f"... ({len(d)}×)"

    def _get_tag_mnemonic(self, val: Tag | dict):
        if isinstance(val, Tag) and val._mnemonic:
            return f"[{val._mnemonic}] "
        return ""

    def _has_error(self, val: Tag | dict) -> bool:
        """Whether a field – or any field inside a nested submenu – failed the last submit."""
        match val:
            case Tag() as tag:
                return tag._error_text is not None
            case dict() as d:
                return any(self._has_error(v) for v in d.values())
        return False

    def run_dialog(self, form: TagDict, title: str = "", submit: bool | str = True) -> TagDict:
        """Let the user edit the form_dict values in a GUI window.
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
                index = self._choose(
                    [
                        f"{self._get_tag_mnemonic(val)}{'* ' if self._has_error(val) else ''}{key}{self._get_tag_val(val)}"
                        for key, val in form.items()
                    ],
                    append_ok=True,
                )
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
        if TerminalMenu is None or self._plain_menu_fallback or self.settings.plain_menu:
            return self._choose_plain(items, title, append_ok, multiple)
        try:
            return self._choose_menu(items, title, append_ok, multiple)
        except NotImplementedError:
            # TerminalMenu needs a real terminal (fails under IDE test runners or piped stdin)
            self._plain_menu_fallback = True
            return self._choose_plain(items, title, append_ok, multiple)

    def _choose_plain(self, items: list, title=None, append_ok=False, multiple: bool = False) -> int | tuple[int]:
        """Numbered menu read through plain input(), for terminals TerminalMenu cannot serve (Windows)."""
        keys: dict[str, int] = {}
        lines = []
        for i, item in enumerate(items):
            if len(item) > 3 and item[0] == "[" and item[2] == "]":  # item already has a shortcut, ex. `[g] foo`
                keys[item[1].lower()] = i
                lines.append(item)
            else:
                lines.append(f"[{i + 1}] {item}")
        for i in range(len(items)):  # positional numbers work even for items displaying a letter shortcut
            keys[str(i + 1)] = i

        print()  # blank line so consecutive menus do not visually clash
        if title:
            print(title)
        if append_ok:
            print("[0] ok")
        if lines:
            print("\n".join(lines))

        if multiple:
            prompt = "Choose (numbers separated by a space):"
        elif append_ok:
            prompt = "Choose (Enter = ok):"
        else:
            prompt = "Choose:"
        while True:
            try:
                # input_timeout, not input() – it reads the raw fd like the rest of the dialog,
                # whereas input() buffers ahead and would swallow input meant for the next prompt
                ans = input_timeout(prompt).strip().lower()
            except EOFError:
                raise Cancelled
            if append_ok and ans in ("", "0", "ok"):
                raise Submit
            if multiple:
                tokens = re.split(r"[,\s]+", ans) if ans else []
                if all(t in keys for t in tokens):
                    return tuple(sorted({keys[t] for t in tokens}))
            elif ans in keys:
                return keys[ans]
            print("Not understood, choose again.")

    def _choose_menu(self, items: list, title=None, append_ok=False, multiple: bool = False) -> int | tuple[int]:
        # TerminalMenu treats '|' as a preview-argument separator; escape so it renders literally
        items = [item.replace("|", "\\|") for item in items]
        it = items
        kwargs = {}
        if not multiple:
            if len(items) < 10:
                # use number as shorcuts when no shortcuts are given `[c]`
                it = [
                    (
                        item
                        if item.startswith("[")  # field already starts with a shortcut, ex. `[f] foo`
                        else f"[{i+1}] {item}"
                    )  # add a number shorctu, ex. `[1] foo`
                    for i, item in enumerate(items)
                ]
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
                index = tuple(i - 1 for i in index)
        else:
            index: int
            if append_ok:
                if index == 0:
                    raise Submit
                index -= 1
        return index

    def _determine_mnemonic(self, form: TagDict, also_nones=False):
        if self.settings.mnemonic_over_number is False:
            return
        super()._determine_mnemonic(form, also_nones=also_nones and self.settings.mnemonic_over_number is True)
