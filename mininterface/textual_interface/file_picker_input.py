from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Tree, Static
from textual.widgets.tree import TreeNode


from ..tag.path_tag import PathTag
from .widgets import TagWidgetWithInput

if TYPE_CHECKING:
    from .adaptor import TextualAdaptor


class FileBrowser(Vertical):
    """A file browser dialog."""

    BINDINGS = [
        Binding("enter", "select", "Select"),
        Binding("escape", "close", "Close"),
        Binding("space", "toggle_expand", "Toggle Expand"),
        Binding("backspace", "parent_dir", "Parent Directory"),
    ]

    DEFAULT_CSS = """
    FileBrowser {
        height: auto;
        min-height: 10;
        max-height: 20;
        border: solid $accent;
        background: $surface;
        margin: 1;
        padding: 0;
        width: 100%;
        dock: bottom;
    }

    FileBrowser Tree {
        height: auto;
        max-height: 14;
        width: 100%;
        overflow-y: scroll;
        background: $surface;
        padding: 0 1;
    }

    FileBrowser Static#tree_header {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        align: left top;
        padding: 0 1;
    }

    FileBrowser Static#status_bar {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        align: center bottom;
        padding: 0 1;
    }

    FileBrowser #nav_buttons {
        height: 1;
        width: 100%;
    }

    FileBrowser Button {
        margin: 0 1 0 0;
    }
    """

    def __init__(self, tag: PathTag):
        super().__init__()
        self.tag = tag
        self.selected_paths = []

        self._start_path = self._get_start_path_from_tag()

        self._tree = None
        self._header = None
        self._status = None
        self._search_prefix = ""
        self._search_timer = None
        self._is_quick_search = False

    def _get_start_path_from_tag(self) -> Path:
        """Get the starting path from the tag value or fallback to home directory."""
        try:
            tag_value = self.tag._get_ui_val()

            if isinstance(tag_value, list) and tag_value:
                path = Path(tag_value[0])
            elif tag_value:
                path = Path(tag_value)
            else:
                return Path.home()

            if path.exists() and path.is_file():
                return path.parent
            elif path.exists() and path.is_dir():
                return path
            else:
                current = path
                while current != current.parent and not current.exists():
                    current = current.parent
                return current
        except Exception:
            return Path.home()

    def _update_status(self) -> None:
        """Update the header and status bar with current information."""
        current_dir = f"📂 {self._start_path}"

        if self._header:
            self._header.update(current_dir)
            self._header.refresh()

        if self.tag.multiple:
            count = len(self.selected_paths)
            if count == 0:
                status_text = "Multiple selection enabled. Use Enter or click to select files."
            else:
                status_text = f"Selected {count} items. Press Enter to finish."
        else:
            status_text = "Navigate with arrows. Press Enter to select."

        if self._search_prefix:
            status_text = f"Searching: {self._search_prefix}... | {status_text}"

        if self._status:
            self._status.update(status_text)
            self._status.refresh()

    def compose(self) -> ComposeResult:
        """Create and yield the tree widget with a dynamic header."""
        nav_container = Horizontal(id="nav_buttons")
        yield nav_container

        self._header = Static(f"📂 {self._start_path}", id="tree_header")
        yield self._header

        self._tree = Tree("")
        self._tree.root.expand()
        try:
            self._add_directory(self._start_path, self._tree.root)
        except Exception as e:
            self._tree.root.add(f"⚠️ Error: {str(e)}")
        yield self._tree

        self._status = Static("", id="status_bar")
        self._update_status()
        yield self._status

    def _add_directory(self, path: Path, node: TreeNode) -> None:
        """Add directory contents to the tree."""
        try:
            paths = sorted(
                path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )

            for item in paths:
                if item.name.startswith('.'):
                    continue

                try:
                    if item.is_dir():
                        branch = node.add(f"📁 {item.name}", data=item, expand=False)
                        try:
                            if next(item.iterdir(), None) is not None:
                                branch.add("Loading...")
                        except (PermissionError, OSError):
                            pass
                    else:
                        if not self.tag.is_dir:
                            # Add file nodes as non-expandable
                            node.add(f"📄 {item.name}", data=item, expand=False).allow_expand = False
                except (PermissionError, OSError):
                    continue

        except PermissionError:
            node.add("⚠️ Permission denied")
        except Exception as e:
            node.add(f"⚠️ Error: {str(e)}")

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Called when a node is expanded."""
        node = event.node
        if not node.data:
            return

        node.remove_children()
        self._add_directory(node.data, node)

    def action_select(self) -> None:
        """Select the currently focused node."""
        if not self._tree or not self._tree.cursor_node:
            return
        self.on_tree_node_selected(Tree.NodeSelected(node=self._tree.cursor_node))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if self._is_quick_search:
            return

        node = event.node
        if not node.data:
            return

        path = node.data
        if not isinstance(path, Path):
            try:
                path = Path(str(path))
            except Exception:
                return

        # Handle directories
        if path.is_dir():
            if self.tag.is_dir:
                # Directory selection mode: select the directory
                if self.tag.multiple:
                    if path in self.selected_paths:
                        self.selected_paths.remove(path)
                    else:
                        self.selected_paths.append(path)
                    self._update_status()
                    if hasattr(self.parent, "input"):
                        self.parent._update_value_from_browser(self.selected_paths)
                else:
                    if hasattr(self.parent, "input"):
                        self.parent._update_value_from_browser(path)
                    self.remove()
            else:
                # File selection mode: navigate into directory
                self._start_path = path
                self._update_status()
                if not node.is_expanded:
                    node.expand()
                    if not node.children:
                        self._add_directory(path, node)
            return

        # Handle files (only in file selection mode)
        if not self.tag.is_dir:
            if self.tag.multiple:
                if path in self.selected_paths:
                    self.selected_paths.remove(path)
                else:
                    self.selected_paths.append(path)
                self._update_status()
                if hasattr(self.parent, "input"):
                    self.parent._update_value_from_browser(self.selected_paths)
            else:
                if hasattr(self.parent, "input"):
                    self.parent._update_value_from_browser(path)
                self.remove()

    def action_close(self) -> None:
        """Close the file browser."""
        self.remove()

    def action_toggle_expand(self) -> None:
        """Toggle expand/collapse of the current node."""
        if self._tree and self._tree.cursor_node:
            if self._tree.cursor_node.is_expanded:
                self._tree.cursor_node.collapse()
            else:
                self._tree.cursor_node.expand()

    def on_key(self, event) -> None:
        """Handle key events for quick search."""
        key = event.key
        if len(key) == 1 and key.isprintable():
            self._search_prefix += key
            self._search_timer = self.set_timer(1.0, self._reset_search)
            self._find_matching_node()
            self._update_status()

    def _find_matching_node(self) -> None:
        """Find and focus the first node that starts with the search prefix without triggering selection."""
        if not self._tree or not self._search_prefix:
            return

        def walk_nodes(node, depth=0):
            """Walk through nodes in a depth-first manner, yielding nodes in display order."""
            if depth > 0:  # Skip the root node
                yield node
            for child in node.children:
                yield from walk_nodes(child, depth + 1)

        # Get all nodes in display order (excluding the root)
        nodes = list(walk_nodes(self._tree.root))

        # Find the first matching node
        for node in nodes:
            label = node.label.plain
            if label.startswith(("📁", "📄")):
                label = label[2:].strip()

            if label.lower().startswith(self._search_prefix.lower()):
                # set the flag to indicate this is a quick search focus change
                self._is_quick_search = True
                self._tree.select_node(node)
                self._tree.scroll_to_node(node)
                self._is_quick_search = False
                break

    def _reset_search(self) -> None:
        """Reset the search prefix after a timeout."""
        self._search_prefix = ""
        self._search_timer = None
        self._update_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button presses."""
        if event.button.id == "goto_root":
            self._navigate_to(Path("/"))
        elif event.button.id == "goto_home":
            self._navigate_to(Path.home())
        elif event.button.id == "goto_parent":
            self._navigate_to(self._start_path.parent)

    def _navigate_to(self, path: Path) -> None:
        """Navigate to a specific directory."""
        if not path.exists() or not path.is_dir():
            return

        self._start_path = path
        self._tree.clear()
        self._tree.root.expand()
        try:
            self._add_directory(path, self._tree.root)
        except Exception as e:
            self._tree.root.add(f"⚠️ Error: {str(e)}")

        self._update_status()
        self.refresh()

    def action_parent_dir(self) -> None:
        """Navigate to parent directory."""
        self._navigate_to(self._start_path.parent)

    def on_tree_node_activated(self, event: Tree.NodeSelected) -> None:
        """Handle double-click on tree nodes."""
        node = event.node
        if not node.data:
            return

        path = node.data
        if path.is_dir():
            self._navigate_to(path)
        else:
            self.on_tree_node_selected(Tree.NodeSelected(self._tree, node))


def FilePickerInputFactory(adaptor: "TextualAdaptor", tag: PathTag, **kwargs):
    class FilePickerInput(TagWidgetWithInput, Horizontal):
        """A custom widget that combines an input field with a file picker button."""

        BINDINGS = [Binding(adaptor.settings.toggle_widget, "on_button_pressed", "Toggle picker")]

        def action_on_button_pressed(self):
            self.button.press()

        DEFAULT_CSS = """
        FilePickerInput {
            layout: horizontal;
            height: auto;
            width: 100%;
        }

        FilePickerInput Input {
            width: 80%;
            margin: 1;
        }

        FilePickerInput Button {
            width: 20%;
            margin: 1;
            background: $accent;
            color: $text;
        }
        """

        def __init__(self, tag: PathTag, **kwargs):
            super().__init__(tag)

            initial_value = str(tag._get_ui_val())
            self.input = Input(value=initial_value, placeholder=kwargs.get("placeholder", ""))
            self.button = Button("...", variant="primary", id="file_picker")
            self.browser = None
            # Store selected paths at the input widget level
            self.selected_paths = []
            if tag.multiple and tag._get_ui_val():
                # Initialize selected paths from existing value
                try:
                    paths = eval(str(tag._get_ui_val()))
                    if isinstance(paths, list):
                        self.selected_paths = [Path(p) for p in paths]
                except (ValueError, SyntaxError):
                    pass

        def compose(self) -> ComposeResult:
            """Compose the widget layout."""
            yield self.input
            yield self.button

        def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button press event."""
            if event.button.id == "file_picker":
                if not self.browser:
                    self.browser = FileBrowser(self.tag)
                    # Pass the current selections to the browser
                    self.browser.selected_paths = self.selected_paths.copy()
                    self.mount(self.browser)
                    self.refresh()
                    self.set_timer(0.1, self._focus_tree)
                else:
                    # Store the current selections before closing
                    self.selected_paths = self.browser.selected_paths.copy()
                    self.browser.remove()
                    self.browser = None
                    self.refresh()

        def _focus_tree(self) -> None:
            """Focus the tree widget after it's mounted."""
            if self.browser and self.browser._tree:
                self.browser._tree.focus()
                # Select the first node if it exists
                if self.browser._tree.root.children:
                    self.browser._tree.select_node(self.browser._tree.root.children[0])

        def get_ui_value(self):
            """Get the current value of the input field."""
            return self.input.value

        def _update_value_from_browser(self, path_value):
            """Update the value from browser selection directly, bypassing validation."""
            if isinstance(path_value, list):
                # Update our stored selections
                self.selected_paths = path_value.copy()
                self.input.value = str([str(p) for p in path_value])
            else:
                self.input.value = str(path_value)

    return FilePickerInput(tag, **kwargs)
