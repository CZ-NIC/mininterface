from typing import TYPE_CHECKING
from .._lib.auxiliary import flatten
from .._lib.form_dict import tagdict_to_widgetdict
from .widgets import TagWidget


from textual import events
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Checkbox, Footer, Header, Input, Label, RadioSet, Rule, SelectionList, Static

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor
    from .textual_app import TextualApp, WidgetList


class FormContents(Static):

    def __init__(self, adaptor: "TextualAdaptor", widgets: "WidgetList", focusable_: "WidgetList"):
        super().__init__()
        self.app: "TextualApp"
        self.title = adaptor.facet._title  # NOTE where the title should be – rather here?
        self.widgets = widgets
        self.focusable_ = focusable_
        """ A subset of self.widgets"""
        self.focused_i: int = 0
        self.adaptor = adaptor
        self.output = Static("")

    def compose(self) -> ComposeResult:
        # prepare widgets
        # since textual 1.0.0 we have to build widgets not earlier than the context app is ready

        self.widgets.clear()
        self.widgets.extend(flatten(tagdict_to_widgetdict(
            self.adaptor.facet._form, self.adaptor.widgetize), include_keys=self.adaptor.header))

        # there are multiple sections in the list, <hr>ed by Rule elements. However, the first takes much space.
        if len(self.widgets) and isinstance(self.widgets[0], Rule):
            self.widgets.pop(0)

        # start yielding widgets
        if self.title:
            yield Header()
        yield self.output  # NOTE not used
        yield Footer()

        if text := self.adaptor.interface._redirected.join():
            yield Label(text, id="buffered_text")
        with VerticalScroll():
            yield from self.adaptor.layout_elements
            for i, fieldt in enumerate(self.widgets):
                if isinstance(fieldt, Input):
                    yield Label(fieldt.placeholder)
                # NOTE MyRadioSet not shown now: add name in widgetize and display here
                # NOTE: has this something to do with the PathTag?
                elif hasattr(fieldt, "tag") and fieldt.tag.label and not isinstance(fieldt, Input):
                    yield Label(fieldt.tag.label)
                yield fieldt
                if isinstance(fieldt, TagWidget) and (arb := fieldt._arbitrary):
                    yield arb
                if isinstance(fieldt, TagWidget) and (desc := fieldt.tag.description):
                    yield Label(desc)
                yield Label("")
        self.focusable_.clear()
        self.focusable_.extend(w for w in self.widgets if isinstance(w, (Input, TagWidget)))

    def on_mount(self):
        self.widgets[self.focused_i].focus()

    def on_key(self, event: events.Key) -> None:
        f = self.focusable_
        ff = self.app.focused
        try:
            index = f.index(ff)
        except ValueError:  # probably some other element were focused
            return
        match event.key:
            # Go up and down the form.
            # With the exception of the RadioSet, there keep the default behavior,
            # traversing its elements, unless we are at the edge.
            case "down":
                # (Unfortunaly, I don't know how to implement allowing navigation directly to the RadioSet and SelectionList.)
                if (not isinstance(ff, RadioSet) or ff._selected == len(ff._nodes) - 1) \
                        and not isinstance(ff, SelectionList):
                    f[(index + 1) % len(f)].focus()
                    event.stop()
            case "up":
                if (not isinstance(ff, RadioSet) or ff._selected == 0) \
                        and not isinstance(ff, SelectionList):
                    f[(index - 1) % len(f)].focus()
                    event.stop()
            case "enter":
                # NOTE a multiline input might be
                # isinstance(self.focused,
                if self.app.submit:
                    self.app.action_confirm()
                    event.stop()
            case letter if len(letter) == 1:  # navigate by letters
                for inp_ in f[index+1:] + f[:index]:
                    match inp_:
                        case Checkbox():
                            label = inp_.label
                        case TagWidget():
                            label = inp_.tag.label
                        case _:
                            label = ""
                    if str(label).casefold().startswith(letter):
                        inp_.focus()
                        break
