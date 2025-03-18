from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Tree, Static
from textual.widgets.tree import TreeNode
from pathlib import Path
from .widgets import Changeable
from textual.app import ComposeResult
from ..types import PathTag
from textual.binding import Binding


class FileBrowser(Vertical):
    """A file browser dialog."""

    # Add key bindings for easier navigation
    BINDINGS = [
        Binding("enter", "select", "Select"),
        Binding("escape", "close", "Close"),
        Binding("space", "toggle_expand", "Toggle Expand"),
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
        width: 100%;
        overflow-y: scroll;
        background: $surface;
        padding: 0 1;
    }

    FileBrowser Static {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        align: center bottom;
        padding: 0 1;
    }
    """

    def __init__(self, tag: PathTag):
        super().__init__()
        self._link = tag
        self.selected_paths = []
        self._start_path = Path.home()
        self._tree = None
        self._status = Static("")
        self._search_prefix = ""
        self._search_timer = None
        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar with current information."""
        if self._link.multiple:
            count = len(self.selected_paths)
            if count == 0:
                status_text = "Multiple selection enabled. Use Enter or click to select files."
            else:
                status_text = f"Selected {count} items. Press Enter to finish."
        else:
            status_text = "Navigate with arrows. Press Enter to select."

        # Show search info if active
        if self._search_prefix:
            status_text = f"Searching: {self._search_prefix}... | {status_text}"

        if hasattr(self, "_status"):
            self._status.update(status_text)

    def compose(self) -> ComposeResult:
        """Create and yield the tree widget."""
        self._tree = Tree("📂 Files")
        self._tree.root.expand()
        # Add initial directory contents
        try:
            self._add_directory(self._start_path, self._tree.root)
        except Exception as e:
            self._tree.root.add(f"⚠️ Error: {str(e)}")
        yield self._tree

        # Add status bar
        self._status = Static("")
        self._update_status()
        yield self._status

    def _add_directory(self, path: Path, node: TreeNode) -> None:
        """Add directory contents to the tree."""
        try:
            # Sort directories first, then files
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
                        # Check if directory has contents before adding dummy node
                        if next(item.iterdir(), None) is not None:
                            branch.add("Loading...")
                    else:
                        if not self._link.is_dir:  # Only show files if not dir-only
                            node.add(f"📄 {item.name}", data=item)
                except PermissionError:
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

        # Remove dummy nodes
        node.remove_children()
        # Add actual directory contents
        self._add_directory(node.data, node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Called when a node is selected."""
        node = event.node
        if not node.data:
            return

        # Ensure node.data is a Path object
        path = node.data
        if not isinstance(path, Path):
            try:
                path = Path(str(path))
            except Exception:
                # If conversion fails, just return
                return

        # Skip directories if we're only looking for files
        if self._link.is_dir is False and path.is_dir():
            return

        # Skip files if we're only looking for directories
        if self._link.is_dir is True and not path.is_dir():
            return

        # For multiple selection
        if self._link.multiple:
            # Toggle selection
            if path in self.selected_paths:
                self.selected_paths.remove(path)
            else:
                self.selected_paths.append(path)

            # Update status bar
            self._update_status()

            # Update parent input field with selected paths
            if hasattr(self.parent, "input"):
                # Update values without validation
                self.parent._update_value_from_browser(self.selected_paths)
        # For single selection
        else:
            # Set the selected path
            if hasattr(self.parent, "input"):
                # Update value without validation
                self.parent._update_value_from_browser(path)
            # Remove the file browser after selection
            self.remove()

    def action_select(self) -> None:
        """Select the currently focused node."""
        if self._tree and self._tree.cursor_node:
            self.on_tree_node_selected(Tree.NodeSelected(self._tree, self._tree.cursor_node))

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
        # Check if it's a printable character
        key = event.key
        if len(key) == 1 and key.isprintable():
            self._search_prefix += key
            if self._search_timer:
                self.remove_timer(self._search_timer)
            self._search_timer = self.set_timer(1.0, self._reset_search)
            self._find_matching_node()
            self._update_status()

    def _reset_search(self) -> None:
        """Reset the search prefix."""
        self._search_prefix = ""
        self._search_timer = None
        self._update_status()

    def _find_matching_node(self) -> None:
        """Find and focus the first node that starts with the search prefix."""
        if not self._tree or not self._search_prefix:
            return

        # Look through all visible nodes
        for node in self._tree.walk_nodes():
            if node is self._tree.root:
                continue

            # Get the node label text (remove emoji prefix if present)
            label = node.label.plain
            if label.startswith(("📁", "📄")):
                label = label[2:].strip()

            # Check if it matches the prefix
            if label.lower().startswith(self._search_prefix.lower()):
                self._tree.cursor_node = node
                self._tree.scroll_to_node(node)
                break


class FilePickerInput(Horizontal, Changeable):
    """A custom widget that combines an input field with a file picker button."""

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
        super().__init__()
        self._link = tag
        initial_value = ""
        if tag.val is not None:
            if isinstance(tag.val, list):
                initial_value = ", ".join(str(p) for p in tag.val)
            else:
                initial_value = str(tag.val)
        self.input = Input(value=initial_value, placeholder=kwargs.get("placeholder", ""))
        self.button = Button("Browse", variant="primary", id="file_picker")
        self.browser = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield self.input
        yield self.button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press event."""
        if event.button.id == "file_picker":
            if not self.browser:
                # Create and mount the file browser
                self.browser = FileBrowser(self._link)
                self.mount(self.browser)
                # Ensure it's displayed after mounting
                self.refresh()

                # Focus the tree widget after a short delay to ensure it's rendered
                self.set_timer(0.1, self._focus_tree)
            else:
                self.browser.remove()
                self.browser = None
                self.refresh()

    def _focus_tree(self) -> None:
        """Focus the tree widget after it's mounted."""
        if self.browser and self.browser._tree:
            self.browser._tree.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input == self.input:
            self.trigger_change()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # This is triggered when Enter is pressed in the input
        self.trigger_change()
        if hasattr(self._link, 'facet'):
            self._link.facet.submit()

    def get_ui_value(self):
        """Get the current value of the input field."""
        if not self.input.value:
            return None

        value = self.input.value.strip()
        if not value:
            return None

        # For multiple path selection
        if self._link.multiple:
            # Split by comma and clean up
            path_strings = [p.strip() for p in value.split(',') if p.strip()]
            if not path_strings:
                return None

            # Try to convert each path to a Path object
            try:
                return [Path(p) for p in path_strings]
            except Exception:
                # If conversion fails, return the string values
                return path_strings

        # For single path selection
        try:
            return Path(value)
        except Exception:
            # If conversion fails, return the string value
            return value

    def _update_value_from_browser(self, path_value):
        """Update the value from browser selection directly, bypassing validation."""
        if not self._link:
            return

        # Fix the annotation to match the actual value type
        if isinstance(path_value, list):
            self._link.annotation = list[Path]
        else:
            self._link.annotation = Path

        # For multiple paths
        if isinstance(path_value, list):
            # Set the input value
            paths_str = ", ".join(str(p) for p in path_value)
            self.input.value = paths_str

            # Directly set the tag's value without validation
            self._link.val = path_value

            # Directly call callback if exists
            if hasattr(self._link, '_callback') and self._link._callback:
                self._link._callback(self._link)
        # For single path
        else:
            # Set the input value
            self.input.value = str(path_value)

            # Directly set the tag's value without validation
            self._link.val = path_value

            # Directly call callback if exists
            if hasattr(self._link, '_callback') and self._link._callback:
                self._link._callback(self._link)

    def trigger_change(self):
        """Override trigger_change to prevent validation errors."""
        if tag := self._link:
            # Get the current value without validation
            value = self.get_ui_value()

            # Fix the annotation to match the actual value type
            if isinstance(value, list) and all(isinstance(p, Path) for p in value):
                tag.annotation = list[Path]
            elif isinstance(value, Path):
                tag.annotation = Path

            # Directly set the value on the tag and trigger change
            if isinstance(value, list) and tag.multiple:
                tag.val = value
            elif value is not None:
                tag.val = value

            # Only manually trigger the change callback without validation
            if hasattr(tag, '_callback') and tag._callback:
                tag._callback(tag)
