from mininterface._lib.shortcuts import convert_to_tkinter_shortcut, convert_to_textual_shortcut
from shared import TestAbstract


class TestShortcuts(TestAbstract):
    def test_basic_modifiers(self):
        """Test basic modifier key conversions."""
        # Textual to Tkinter
        self.assertEqual(convert_to_tkinter_shortcut("ctrl+t"), "<Control-t>")
        self.assertEqual(convert_to_tkinter_shortcut("alt+f"), "<Alt-f>")
        self.assertEqual(convert_to_tkinter_shortcut("shift+s"), "<Shift-s>")

        # Tkinter to Textual
        self.assertEqual(convert_to_textual_shortcut("<Control-t>"), "ctrl+t")
        self.assertEqual(convert_to_textual_shortcut("<Alt-f>"), "alt+f")
        self.assertEqual(convert_to_textual_shortcut("<Shift-s>"), "shift+s")

    def test_function_keys(self):
        """Test function key conversions."""
        # Textual to Tkinter
        self.assertEqual(convert_to_tkinter_shortcut("f4"), "<F4>")
        self.assertEqual(convert_to_tkinter_shortcut("f12"), "<F12>")

        # Tkinter to Textual
        self.assertEqual(convert_to_textual_shortcut("<F4>"), "f4")
        self.assertEqual(convert_to_textual_shortcut("<F12>"), "f12")

    def test_multiple_modifiers(self):
        """Test multiple modifier key combinations."""
        # Textual to Tkinter
        self.assertEqual(convert_to_tkinter_shortcut("ctrl+alt+t"), "<Control-Alt-t>")
        self.assertEqual(convert_to_tkinter_shortcut("ctrl+shift+s"), "<Control-Shift-s>")

        # Tkinter to Textual
        self.assertEqual(convert_to_textual_shortcut("<Control-Alt-t>"), "ctrl+alt+t")
        self.assertEqual(convert_to_textual_shortcut("<Control-Shift-s>"), "ctrl+shift+s")

    def test_macos_keys(self):
        """Test macOS specific key conversions."""
        # Textual to Tkinter
        self.assertEqual(convert_to_tkinter_shortcut("cmd+s"), "<Command-s>")
        self.assertEqual(convert_to_tkinter_shortcut("meta+t"), "<Meta-t>")

        # Tkinter to Textual
        self.assertEqual(convert_to_textual_shortcut("<Command-s>"), "cmd+s")
        self.assertEqual(convert_to_textual_shortcut("<Meta-t>"), "meta+t")

    def test_case_insensitivity(self):
        """Test case insensitivity in conversions."""
        # Textual to Tkinter
        self.assertEqual(convert_to_tkinter_shortcut("CTRL+T"), "<Control-t>")
        self.assertEqual(convert_to_tkinter_shortcut("Ctrl+t"), "<Control-t>")
        self.assertEqual(convert_to_tkinter_shortcut("cTrL+t"), "<Control-t>")

        # Tkinter to Textual
        self.assertEqual(convert_to_textual_shortcut("<CONTROL-t>"), "ctrl+t")
        self.assertEqual(convert_to_textual_shortcut("<Control-t>"), "ctrl+t")
        self.assertEqual(convert_to_textual_shortcut("<CoNtRoL-t>"), "ctrl+t")

    def test_roundtrip_conversion(self):
        """Test that converting back and forth gives the same result."""
        test_shortcuts = [
            "ctrl+t",
            "alt+f",
            "shift+s",
            "f4",
            "ctrl+alt+t",
            "cmd+s",
            "meta+t"
        ]

        for shortcut in test_shortcuts:
            tk_shortcut = convert_to_tkinter_shortcut(shortcut)
            back_to_textual = convert_to_textual_shortcut(tk_shortcut)
            self.assertEqual(back_to_textual, shortcut)

    def test_invalid_input(self):
        """Test handling of invalid inputs."""
        with self.assertRaises(AttributeError):
            convert_to_tkinter_shortcut(None)

        with self.assertRaises(AttributeError):
            convert_to_textual_shortcut(None)

        # Empty string should be handled gracefully
        self.assertEqual(convert_to_tkinter_shortcut(""), "<>")
        self.assertEqual(convert_to_textual_shortcut("<>"), "")
