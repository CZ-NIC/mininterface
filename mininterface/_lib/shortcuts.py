def convert_to_tkinter_shortcut(shortcut: str) -> str:
    """Convert a textual shortcut format to tkinter format.

    Args:
        shortcut: Shortcut in textual format (e.g., "ctrl+t", "f4")

    Returns:
        Shortcut in tkinter format (e.g., "<Control-t>", "<F4>")
    """
    # Handle function keys
    if shortcut.startswith("f") and shortcut[1:].isdigit():
        return f"<{shortcut.upper()}>"

    # Handle modifier keys
    mods = {
        "ctrl": "Control",
        "alt": "Alt",
        "shift": "Shift",
        "cmd": "Command",  # For macOS
        "meta": "Meta",
    }

    parts = shortcut.lower().split("+")
    keys = [mods.get(p, p) for p in parts]
    modifiers = keys[:-1]
    key = keys[-1]

    return f"<{'-'.join(modifiers + [key])}>"


def convert_to_textual_shortcut(shortcut: str) -> str:
    """Convert a tkinter shortcut format to textual format.

    Args:
        shortcut: Shortcut in tkinter format (e.g., "<Control-t>", "<F4>")

    Returns:
        Shortcut in textual format (e.g., "ctrl+t", "f4")
    """
    shortcut = shortcut.strip("<>")

    # Handle function keys
    if shortcut.startswith("F") and shortcut[1:].isdigit():
        return shortcut.lower()

    # Handle modifier keys
    mods = {
        "Control": "ctrl",
        "Alt": "alt",
        "Shift": "shift",
        "Command": "cmd",  # For macOS
        "Meta": "meta",
    }

    parts = shortcut.split("-")
    # Convert each part to its proper form
    keys = [mods.get(part.title(), part.lower()) for part in parts]

    return "+".join(keys)
