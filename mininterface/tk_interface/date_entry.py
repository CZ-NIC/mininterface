import tkinter as tk
import re
from datetime import datetime

try:
    from tkcalendar import Calendar
except ImportError:
    Calendar = None

class DateEntry(tk.Frame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.create_widgets()
        self.pack(expand=True, fill=tk.BOTH)
        self.bind_all_events()

    def create_widgets(self):
        self.spinbox = tk.Spinbox(self, font=("Arial", 16), width=30, wrap=True)
        self.spinbox.pack(padx=20, pady=20)
        self.spinbox.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4])

        # Bind up/down arrow keys
        self.spinbox.bind("<Up>", self.increment_date)
        self.spinbox.bind("<Down>", self.decrement_date)

        # Bind mouse click on spinbox arrows
        self.spinbox.bind("<ButtonRelease-1>", self.on_spinbox_click)

        # Bind key release event to update calendar when user changes the input field
        self.spinbox.bind("<KeyRelease>", self.on_spinbox_change)

        # Toggle calendar button
        self.toggle_button = tk.Button(self, text="Show/Hide Calendar", command=self.toggle_calendar)
        self.toggle_button.pack(pady=10)

        if Calendar:
            self.create_calendar()

    def bind_all_events(self):
        # Copy to clipboard with ctrl+c
        self.bind_all("<Control-c>", self.copy_to_clipboard)

        # Select all in the spinbox with ctrl+a
        self.bind_all("<Control-a>", lambda event: self.select_all())

        # Paste from clipboard with ctrl+v
        self.bind_all("<Control-v>", lambda event: self.paste_from_clipboard())

        # Toggle calendar widget with ctrl+shift+c
        self.bind_all("<Control-Shift-c>", lambda event: self.toggle_calendar())

    def create_calendar(self):
        # Create a frame to hold the calendar
        self.frame = tk.Frame(self)
        self.frame.pack(padx=20, pady=20, expand=True, fill=tk.BOTH)

        # Add a calendar widget
        self.calendar = Calendar(self.frame, selectmode='day', date_pattern='yyyy-mm-dd')
        self.calendar.place(relwidth=0.7, relheight=0.8, anchor='n', relx=0.5)

        # Bind date selection event
        self.calendar.bind("<<CalendarSelected>>", self.on_date_select)

        # Initialize calendar with the current date
        self.update_calendar(self.spinbox.get())

    def toggle_calendar(self, event=None):
        if Calendar:
            if hasattr(self, 'frame') and self.frame.winfo_ismapped():
                self.frame.pack_forget()
            else:
                self.frame.pack(padx=20, pady=20, expand=True, fill=tk.BOTH)

    def increment_date(self, event=None):
        self.change_date(1)

    def decrement_date(self, event=None):
        self.change_date(-1)

    def change_date(self, delta):
        date_str = self.spinbox.get()
        caret_pos = self.spinbox.index(tk.INSERT)

        # Split the date string by multiple delimiters
        split_input = re.split(r'[- :.]', date_str)

        # Determine which part of the date the caret is on
        # 0 -> year
        # 1 -> month
        # 2 -> day
        # 3 -> hour
        # 4 -> minute
        # 5 -> second
        # 6 -> microsecond
        if caret_pos < 5:
            part_index = 0
        elif caret_pos < 8:
            part_index = 1
        elif caret_pos < 11:
            part_index = 2
        elif caret_pos < 14:
            part_index = 3
        elif caret_pos < 17:
            part_index = 4
        elif caret_pos < 20:
            part_index = 5
        else:
            part_index = 6

        # Increment or decrement the relevant part
        number = int(split_input[part_index])
        new_number = number + delta
        split_input[part_index] = str(new_number).zfill(len(split_input[part_index]))

        # Reconstruct the date string
        new_date_str = f"{split_input[0]}-{split_input[1]}-{split_input[2]} {split_input[3]}:{split_input[4]}:{split_input[5]}.{split_input[6][:2]}"

        # Validate the new date
        try:
            datetime.strptime(new_date_str, '%Y-%m-%d %H:%M:%S.%f')
            self.spinbox.delete(0, tk.END)
            self.spinbox.insert(0, new_date_str)
            self.spinbox.icursor(caret_pos)
            if Calendar:
                self.update_calendar(new_date_str)
        except ValueError:
            pass

    def on_spinbox_click(self, event):
        # Check if the click was on the spinbox arrows
        if self.spinbox.identify(event.x, event.y) == "buttonup":
            self.increment_date()
        elif self.spinbox.identify(event.x, event.y) == "buttondown":
            self.decrement_date()

    def on_date_select(self, event):
        selected_date = self.calendar.selection_get()
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        new_date_str = f"{selected_date.strftime('%Y-%m-%d')} {current_time}"
        self.spinbox.delete(0, tk.END)
        self.spinbox.insert(0, new_date_str)
        self.update_calendar(new_date_str)

    def update_calendar(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
            self.calendar.selection_set(date_obj)
        except ValueError:
            pass

    def on_spinbox_change(self, event):
        if Calendar:
            self.update_calendar(self.spinbox.get())

    def copy_to_clipboard(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.spinbox.get())
        self.update()  # now it stays on the clipboard after the window is closed

    def select_all(self, event=None):
        self.spinbox.selection_range(0, tk.END)
        self.spinbox.focus_set()
        self.spinbox.icursor(0)
        return 'break'

    def paste_from_clipboard(self, event=None):
        self.spinbox.delete(0, tk.END)
        self.spinbox.insert(0, self.clipboard_get())
        return 'break'

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    root.title("Date Editor")

    date_entry = DateEntry(root)
    date_entry.pack(expand=True, fill=tk.BOTH)

    root.mainloop()

