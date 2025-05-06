import tkinter as tk
import re
from datetime import datetime
from typing import TYPE_CHECKING

try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None

from ..tag.datetime_tag import DatetimeTag
if TYPE_CHECKING:
    from mininterface._tk_interface.adaptor import TkAdaptor


class DateEntryFrame(tk.Frame):

    def __init__(self, master, tk_app: "TkAdaptor", tag: DatetimeTag, variable: tk.Variable, **kwargs):
        super().__init__(master, **kwargs)

        self.tk_app = tk_app
        self.tag = tag
        if tag.date and tag.time:
            if tag.full_precision:
                self.datetimeformat = '%Y-%m-%d %H:%M:%S'
            else:
                self.datetimeformat = '%Y-%m-%d %H:%M'
        elif tag.time and not tag.date:
            if tag.full_precision:
                self.datetimeformat = '%H:%M:%S'
            else:
                self.datetimeformat = '%H:%M'
        else:
            self.datetimeformat = '%Y-%m-%d'

        # Date entry
        self.spinbox = self.create_spinbox(variable)

        # Frame holding the calendar
        self.frame = tk.Frame(self)

        # The calendar widget
        if Calendar and tag.date:
            # Toggle calendar button
            tk.Button(self, text="…", command=self.toggle_calendar).grid(row=0, column=1)

            # Add a calendar widget
            self.calendar = Calendar(self.frame, selectmode='day', date_pattern='yyyy-mm-dd')
            # Bind date selection event
            self.calendar.bind("<<CalendarSelected>>", self.on_date_select)
            self.calendar.grid()
            # Initialize calendar with the current date
            self.update_calendar(self.spinbox.get(), self.datetimeformat)
        else:
            self.calendar = None

    def create_spinbox(self, variable: tk.Variable):
        spinbox = tk.Spinbox(self, wrap=True, textvariable=variable)
        spinbox.grid(sticky="we")
        # The default val is handled by DatetimeTag
        # if not variable.get():
        #     spinbox.insert(0, datetime.now().strftime(self.datetimeformat))
        spinbox.focus_set()
        if (not self.tag.date and self.tag.time):
            spinbox.icursor(0)
        else:
            spinbox.icursor(8)

        # Bind up/down arrow keys
        spinbox.bind("<Up>", self.increment_value)
        spinbox.bind("<Down>", self.decrement_value)

        # Bind mouse click on spinbox arrows
        spinbox.bind("<ButtonRelease-1>", self.on_spinbox_click)

        # Bind key release event to update calendar when user changes the input field
        spinbox.bind("<KeyRelease>", self.on_spinbox_change)

        # Toggle calendar widget with ctrl+shift+c
        spinbox.bind("<Control-Shift-C>", self.toggle_calendar)

        # Select all in the spinbox with ctrl+a
        spinbox.bind("<Control-a>", self.select_all)

        # Copy to clipboard with ctrl+c
        spinbox.bind("<Control-c>", self.copy_to_clipboard)

        # Paste from clipboard with ctrl+v
        spinbox.bind("<Control-v>", self.paste_from_clipboard)

        return spinbox

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
        if self.tag.full_precision:
            time_part = re.search(r'\d{2}:\d{2}:\d{2}', input)
        else:
            time_part = re.search(r'\d{2}:\d{2}', input)
        if time_part:
            return time_part.group()
        return False

    def change_date(self, delta):
        date_str = self.spinbox.get()
        caret_pos = self.spinbox.index(tk.INSERT)

        date = self.find_valid_date()
        time = self.find_valid_time()

        if date and not time:
            split_input = re.split(r'[-]', date)
            new_value_str = self.increment_part(split_input, caret_pos, delta, '-')
        elif date and time:
            split_input = re.split(r'[- :]', date_str)
            new_value_str = self.increment_part(split_input, caret_pos, delta, ' ')
        elif not date and time:
            split_input = re.split(r'[:]', time)
            new_value_str = self.increment_part(split_input, caret_pos, delta, ':')
        else:
            return

        # Validate the new date
        try:
            datetime.strptime(new_value_str, self.datetimeformat)
            self.spinbox.delete(0, tk.END)
            self.spinbox.insert(0, new_value_str)
            self.spinbox.icursor(caret_pos)
            if Calendar:
                self.update_calendar(new_value_str, self.datetimeformat)
        except ValueError as e:
            pass

    def increment_part(self, split_input, caret_pos, delta, separator):
        part_index = self.get_part_index(caret_pos)
        if part_index > len(split_input) - 1:
            return separator.join(split_input)

        # Increment or decrement the relevant part
        number = int(split_input[part_index])
        new_number = number + delta
        split_input[part_index] = str(new_number).zfill(len(split_input[part_index]))

        if self.tag.full_precision and separator == ' ':
            return f"{split_input[0]}-{split_input[1]}-{split_input[2]} "\
                f"{split_input[3]}:{split_input[4]}:{split_input[5]}"
        elif separator == ' ':
            return f"{split_input[0]}-{split_input[1]}-{split_input[2]} "\
                f"{split_input[3]}:{split_input[4]}"
        elif separator == ':':
            if self.tag.full_precision:
                return f"{split_input[0]}:{split_input[1]}:{split_input[2]}"
            else:
                return f"{split_input[0]}:{split_input[1]}"
        else:
            return separator.join(split_input)

    def get_part_index(self, caret_pos):
        if self.tag.date and self.tag.time:
            if caret_pos < 5:       # year
                return 0
            elif caret_pos < 8:     # month
                return 1
            elif caret_pos < 11:    # day
                return 2
            elif caret_pos < 14:  # hour
                return 3
            elif caret_pos < 17:  # minute
                return 4
            else:  # second
                return 5
        elif self.tag.date:
            if caret_pos < 5:       # year
                return 0
            elif caret_pos < 8:     # month
                return 1
            elif caret_pos < 11:    # day
                return 2
        elif self.tag.time:
            if caret_pos < 3:       # hour
                return 0
            elif caret_pos < 6:     # minute
                return 1
            else:     # second
                return 2
        return 0

    def on_spinbox_click(self, event):
        # Check if the click was on the spinbox arrows
        if self.spinbox.identify(event.x, event.y) == "buttonup":
            self.increment_value()
        elif self.spinbox.identify(event.x, event.y) == "buttondown":
            self.decrement_value()

    def on_date_select(self, event):

        # find caret position to keep it in the same place
        caret_pos = self.spinbox.index(tk.INSERT)

        selected_date = self.calendar.selection_get().strftime('%Y-%m-%d')
        if self.tag.time:
            time = self.find_valid_time()
            if time:
                selected_date += f" {time}"
            else:
                if self.tag.full_precision:
                    selected_date += " 00:00:00"
                else:
                    selected_date += " 00:00"

        self.spinbox.delete(0, tk.END)
        self.spinbox.insert(0, selected_date)

        # Keep the caret position
        self.spinbox.icursor(caret_pos)

    def on_spinbox_change(self, event):
        if Calendar:
            self.update_calendar(self.spinbox.get())

    def update_calendar(self, date_str, string_format='%Y-%m-%d'):
        if self.tag.date:
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

        label = tk.Label(popup, text=message)
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

    def round_time(self, dt):
        if self.tag.full_precision:
            return dt
        return dt[:-4]
