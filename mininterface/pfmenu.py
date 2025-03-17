import os
import re
import sys

# Try to import colorama for colored output
try:
    from colorama import Fore, init, Style
    COLORAMA_AVAILABLE = True
    init()  # Initialize colorama
except ImportError:
    COLORAMA_AVAILABLE = False

# Try to import rapidfuzz for fuzzy matching
try:
    from rapidfuzz import process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


class _Getch:
    """Gets a single character from standard input. Does not echo to the screen."""

    def __init__(self):
        if os.name == 'nt':  # Windows
            self.impl = _GetchWindows()
        else:  # Unix-like systems
            self.impl = _GetchUnix()

    def __call__(self):
        return self.impl()


class _GetchUnix:
    def __call__(self):
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __call__(self):
        import msvcrt
        return msvcrt.getch()


class Menu:
    def __init__(self, title, options, printhelp=True, autoselect=False, fuzzy=False):
        """
        Initialize the menu.

        @param string       title: The title of the menu
        @param list strings options: The list of menu options
        @param boolean      printhelp: Whether to display help text (default=True)
        @param boolean      autoselect: Automatically select if one option is left (default=False)
        @param boolean      fuzzy: Enable fuzzy search (default=False)
        """
        self.title = title
        self.options = options
        self.printhelp = printhelp
        self.autoselect = autoselect
        self.fuzzy = fuzzy and FUZZY_AVAILABLE  # Enable fuzzy only if rapidfuzz is available
        self.keyboardinput = ""
        self.selected = 0  # Start with the first option selected
        self.current = options  # Filtered options
        self.matches = []  # Fuzzy matches
        self.getch = _Getch()

    def clear_terminal(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def filter_options(self):
        """Filter options based on user input."""
        self.current = [content.replace("\n", "") for content in self.options]

        if self.keyboardinput.strip():
            if self.fuzzy:
                # Use fuzzy matching to filter options
                self.matches = process.extract(
                    self.keyboardinput, self.current, scorer=fuzz.partial_ratio, limit=10
                )
                # Keep only matches with a score above a threshold (e.g., 60)
                self.current = [match[0] for match in self.matches if match[1] > 60]
            else:
                # Use regex to filter options if the input is a valid regex
                try:
                    regex = re.compile(self.keyboardinput, re.IGNORECASE)
                    self.current = [content for content in self.current if regex.search(content)]
                except re.error:
                    # If the regex is invalid, show all options
                    pass

    def highlight_match(self, item):
        """Highlight the matched part of the item."""
        if not COLORAMA_AVAILABLE:
            return item  # Skip highlighting if colorama is not available

        if self.fuzzy:
            match = next((m for m in self.matches if m[0] == item), None)
            if match:
                start = item.lower().find(self.keyboardinput.lower())
                if start != -1:
                    end = start + len(self.keyboardinput)
                    return (
                        item[:start]
                        + Fore.YELLOW
                        + item[start:end]
                        + Style.RESET_ALL
                        + item[end:]
                    )
        else:
            try:
                regex = re.compile(self.keyboardinput, re.IGNORECASE)
                return regex.sub(
                    lambda m: f"{Fore.YELLOW}{m.group(0)}{Style.RESET_ALL}", item
                )
            except re.error:
                pass
        return item

    def display_menu(self):
        """Display the menu."""
        self.clear_terminal()
        self.filter_options()

        # Autoselect if only one option is left
        if self.autoselect and len(self.current) == 1:
            print(f"Automatically selected: {self.current[0]}")
            return self.current[0]

        # Ensure the selected index is within bounds
        self.selected = max(0, min(self.selected, len(self.current) - 1))

        # Print the menu with the current selected entry highlighted
        for i, item in enumerate(self.current):
            highlighted = self.highlight_match(item)
            if i == self.selected:
                if COLORAMA_AVAILABLE:
                    print(f" {Fore.RED}>>{Style.RESET_ALL} {highlighted}")  # Highlight the selected item
                else:
                    print(f" >> {highlighted}")
            else:
                print(f"    {highlighted}")

        # Print the write section
        if self.printhelp:
            print(
                "Default hotkeys: [enter] select, [up/down arrows] navigate, [esc] clean, [Ctrl+c] exit\n"
                "You can also type a valid regex or fuzzy input to filter the options.\n"
            )
        print(self.title + "~$ " + self.keyboardinput + "|")
        print(f"Fuzzy search: {self.fuzzy}")

    def handle_input(self):
        """Handle user input."""
        stdin = self.getch()
        if sys.platform == "win32":
            stdin = stdin.decode("utf-8", "replace")

        # Handle multi-character escape sequences for arrow keys
        if stdin == "\x1b":  # Escape sequence
            next_char = self.getch()
            if next_char == "[":
                arrow_key = self.getch()
                if arrow_key == "A":  # Up arrow
                    self.selected -= 1
                elif arrow_key == "B":  # Down arrow
                    self.selected += 1
            return None

        # Validate input
        if stdin == "\r":  # Enter
            if len(self.current) > 0:
                return self.current[self.selected]
        elif stdin == "\x1b":  # Esc
            self.keyboardinput = ""
            self.selected = 0
        elif stdin == "\x7f" or stdin == "\x08":  # Backspace
            self.keyboardinput = self.keyboardinput[:-1]
        elif stdin == "\x20":  # Space
            self.keyboardinput += " "
        elif stdin == "\x03":  # Ctrl+C
            quit()
        elif stdin == "\t":  # Tab
            if FUZZY_AVAILABLE:
                self.fuzzy = not self.fuzzy
        elif re.fullmatch(r"[^\x00-\x1F\x7F]", stdin):  # Match printable characters
            self.keyboardinput += stdin
            self.selected = 0
        return None

    def run(self):
        """Run the menu."""
        while True:
            result = self.display_menu()
            if result:
                return result
            result = self.handle_input()
            if result:
                return result


# Example usage
if __name__ == "__main__":
    menu_title = "Main Menu"
    menu_options = [
        "add item",
        "remove item",
        "clear all",
        "exit",
        "test 1",
        "volba zde",
        "test 5",
        "test 6",
        "test 7",
    ]

    menu = Menu(menu_title, menu_options, autoselect=False, fuzzy=True)
    selected_option = menu.run()
    print(f"Selected option: {selected_option}")