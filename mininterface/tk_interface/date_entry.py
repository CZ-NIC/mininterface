import tkinter as tk
import re
from datetime import datetime
from typing import TYPE_CHECKING

try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None

from ..types import DatetimeTag
if TYPE_CHECKING:
    from tk_window import TkWindow


class DateEntryFrame(tk.Frame):
    def __init__(self, master, tk_app: "TkWindow", tag: DatetimeTag, variable: tk.Variable, **kwargs):
        super().__init__(master, **kwargs)

        self.tk_app = tk_app
        self.tag = tag

        # Date entry
        self.spinbox = self.create_spinbox(variable)

        # Frame holding the calendar
        self.frame = tk.Frame(self)

        # The calendar widget
        if Calendar:
            # Toggle calendar button
            tk.Button(self, text="…", command=self.toggle_calendar).grid(row=0, column=1)

            # Add a calendar widget
            self.calendar = Calendar(self.frame, selectmode='day', date_pattern='yyyy-mm-dd')
            # Bind date selection event
            self.calendar.bind("<<CalendarSelected>>", self.on_date_select)
            self.calendar.grid()
            # Initialize calendar with the current date
            self.update_calendar(self.spinbox.get(), '%Y-%m-%d %H:%M:%S.%f')
        else:
            self.calendar = None

        self.bind_all_events()

    def create_spinbox(self, variable: tk.Variable):
        spinbox = tk.Spinbox(self, font=("Arial", 16), width=30, wrap=True, textvariable=variable)
        spinbox.grid()
        if not variable.get():
            spinbox.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4])
        spinbox.focus_set()
        spinbox.icursor(8)

        # Bind up/down arrow keys
        spinbox.bind("<Up>", self.increment_value)
        spinbox.bind("<Down>", self.decrement_value)

        # Bind mouse click on spinbox arrows
        spinbox.bind("<ButtonRelease-1>", self.on_spinbox_click)

        # Bind key release event to update calendar when user changes the input field
        spinbox.bind("<KeyRelease>", self.on_spinbox_change)
        return spinbox

    def bind_all_events(self):
        # Copy to clipboard with ctrl+c
        self.bind_all("<Control-c>", self.copy_to_clipboard)

        # Select all in the spinbox with ctrl+a
        self.bind_all("<Control-a>", lambda event: self.select_all())

        # Paste from clipboard with ctrl+v
        self.bind_all("<Control-v>", lambda event: self.paste_from_clipboard())

        # Toggle calendar widget with ctrl+shift+c
        self.bind_all("<Control-Shift-C>", lambda event: self.toggle_calendar())

    def toggle_calendar(self, event=None):
        if not self.calendar:
            return
        if self.calendar.winfo_ismapped():
            self.frame.grid_forget()
        else:
            self.frame.grid(row=1, column=0)
        self.tk_app._refresh_size()
        return

    def increment_value(self, event=None):
        self.change_date(1)

    def decrement_value(self, event=None):
        self.change_date(-1)

    def find_valid_date(self):
        input = self.spinbox.get()
        # use regex to find the date part
        date_part = re.search(r'\d{4}-\d{2}-\d{2}', input)
        if date_part:
            return date_part.group()
        return False

    def find_valid_time(self):
        input = self.spinbox.get()
        # use regex to find the time part
        time_part = re.search(r'\d{2}:\d{2}:\d{2}', input)
        if time_part:
            return time_part.group()
        return False

    def change_date(self, delta):
        date_str = self.spinbox.get()
        caret_pos = self.spinbox.index(tk.INSERT)

        date = self.find_valid_date()
        time = self.find_valid_time()

        if date:
            split_input = re.split(r'[- :.]', date_str)
            part_index = self.get_part_index(caret_pos, len(split_input))

            # Increment or decrement the relevant part
            number = int(split_input[part_index])
            new_number = number + delta
            split_input[part_index] = str(new_number).zfill(len(split_input[part_index]))

            if time:
                new_value_str = f"{split_input[0]}-{split_input[1]}-{split_input[2]} "\
                    f"{split_input[3]}:{split_input[4]}:{split_input[5]}.{split_input[6][:2]}"
                string_format = '%Y-%m-%d %H:%M:%S.%f'
            else:
                new_value_str = f"{split_input[0]}-{split_input[1]}-{split_input[2]}"
                string_format = '%Y-%m-%d'

            # Validate the new date
            try:
                datetime.strptime(new_value_str, string_format)
                self.spinbox.delete(0, tk.END)
                self.spinbox.insert(0, new_value_str)
                self.spinbox.icursor(caret_pos)
                if Calendar:
                    self.update_calendar(new_value_str, string_format)
            except ValueError:
                pass

    def get_part_index(self, caret_pos, split_length):
        if caret_pos < 5:       # year
            return 0
        elif caret_pos < 8:     # month
            return 1
        elif caret_pos < 11:    # day
            return 2
        elif split_length > 3:
            if caret_pos < 14:  # hour
                return 3
            elif caret_pos < 17:  # minute
                return 4
            elif caret_pos < 20:  # second
                return 5
            else:               # millisecond
                return 6
        return 2

    def on_spinbox_click(self, event):
        # Check if the click was on the spinbox arrows
        if self.spinbox.identify(event.x, event.y) == "buttonup":
            self.increment_value()
        elif self.spinbox.identify(event.x, event.y) == "buttondown":
            self.decrement_value()

    def on_date_select(self, event):
        selected_date = self.calendar.selection_get()
        self.spinbox.delete(0, tk.END)
        self.spinbox.insert(0, selected_date.strftime('%Y-%m-%d'))
        self.spinbox.icursor(len(self.spinbox.get()))

    def on_spinbox_change(self, event):
        if Calendar:
            self.update_calendar(self.spinbox.get())

    def update_calendar(self, date_str, string_format='%Y-%m-%d'):
        try:
            date = datetime.strptime(date_str, string_format)
            self.calendar.selection_set(date)
        except ValueError:
            pass

    def copy_to_clipboard(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.spinbox.get())
        self.update()  # now it stays on the clipboard after the window is closed
        self.show_popup("Copied to clipboard")

    def show_popup(self, message):
        popup = tk.Toplevel(self)
        popup.wm_title("")

        label = tk.Label(popup, text=message, font=("Arial", 12))
        label.pack(side="top", fill="x", pady=10, padx=10)

        # Position the popup window in the top-left corner of the widget
        x = self.winfo_rootx()
        y = self.winfo_rooty()

        # Position of the popup window has to be "inside" the main window or it will be focused on popup
        popup.geometry(f"400x100+{x+200}+{y-150}")

        # Close the popup after 2 seconds
        self.after(1000, popup.destroy)

        # Keep focus on the spinbox
        self.spinbox.focus_force()

    def select_all(self, event=None):
        self.spinbox.selection_range(0, tk.END)
        self.spinbox.focus_set()
        self.spinbox.icursor(0)
        return 'break'

    def paste_from_clipboard(self, event=None):
        self.spinbox.delete(0, tk.END)
        self.spinbox.insert(0, self.clipboard_get())
