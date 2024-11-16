import tkinter as tk
from tkcalendar import Calendar
import re
from datetime import datetime

def increment_date(event=None):
    change_date(1)

def decrement_date(event=None):
    change_date(-1)

def change_date(delta):
    date_str = spinbox.get()
    caret_pos = spinbox.index(tk.INSERT)

    # Split the date string by multiple delimiters
    split_input = re.split(r'[- :.]', date_str)

    # Determine which part of the date the caret is on
    # 0 -> day
    # 1 -> month
    # 2 -> year
    # 3 -> hour
    # 4 -> minute
    # 5 -> second
    # 6 -> microsecond
    if caret_pos < 3:
        part_index = 0
    elif caret_pos < 6:
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
        datetime.strptime(new_date_str, '%d-%m-%Y %H:%M:%S.%f')
        spinbox.delete(0, tk.END)
        spinbox.insert(0, new_date_str)
        spinbox.icursor(caret_pos)
        update_calendar(new_date_str)
    except ValueError:
        pass

def on_spinbox_click(event):
    # Check if the click was on the spinbox arrows
    if spinbox.identify(event.x, event.y) == "buttonup":
        increment_date()
    elif spinbox.identify(event.x, event.y) == "buttondown":
        decrement_date()

def on_date_select(event):
    selected_date = calendar.selection_get()
    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-4]
    new_date_str = f"{selected_date.strftime('%d-%m-%Y')} {current_time}"
    spinbox.delete(0, tk.END)
    spinbox.insert(0, new_date_str)
    update_calendar(new_date_str)

def update_calendar(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S.%f')
        calendar.selection_set(date_obj)
    except ValueError:
        pass

def on_spinbox_change(event):
    update_calendar(spinbox.get())

def copy_to_clipboard():
    root.clipboard_clear()
    root.clipboard_append(spinbox.get())
    root.update()  # now it stays on the clipboard after the window is closed

root = tk.Tk()
root.geometry("800x600")
root.title("Date Editor")

spinbox = tk.Spinbox(root, font=("Arial", 16), width=30, wrap=True)
spinbox.pack(padx=20, pady=20)
spinbox.insert(0, datetime.now().strftime("%d-%m-%Y %H:%M:%S.%f")[:-4])

# Bind up/down arrow keys
spinbox.bind("<Up>", increment_date)
spinbox.bind("<Down>", decrement_date)

# Bind mouse click on spinbox arrows
spinbox.bind("<ButtonRelease-1>", on_spinbox_click)

# Bind key release event to update calendar when user changes the input field
spinbox.bind("<KeyRelease>", on_spinbox_change)

# Create a frame to hold the calendar and copy button
frame = tk.Frame(root)
frame.pack(padx=20, pady=20, expand=True, fill=tk.BOTH)

# Add a calendar widget
calendar = Calendar(frame, selectmode='day', date_pattern='dd-mm-yyyy')
calendar.place(relwidth=0.7, relheight=0.8, anchor='n', relx=0.5)

# Bind date selection event
calendar.bind("<<CalendarSelected>>", on_date_select)

# Add a copy-to-clipboard button
copy_button = tk.Button(frame, text="Copy to Clipboard", command=copy_to_clipboard, height=1)
copy_button.place(relwidth=0.2, relheight=0.1, anchor='n', relx=0.5, rely=0.85)

# Initialize calendar with the current date
update_calendar(spinbox.get())

root.mainloop()

