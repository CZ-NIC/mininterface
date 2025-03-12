import tkinter as tk
from ..types import SecretTag
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tk_window import TkWindow
 
class Secret(tk.Frame):
    def __init__(self, master, tk_app: "TkWindow", tag: SecretTag, variable: tk.Variable, **kwargs):
        super().__init__(master, **kwargs)
        self.frame = tk.Frame(self)

    def create_field(self):
        secret_label = tk.Label(self.frame, text = 'Secret')
        secret_var=tk.StringVar()

        icon = tk.PhotoImage(file="../../asset/eye.png", width=25, height=25)
        peek_btn = tk.Button(self.frame, text='Peek', image=icon, width=25, height=25, highlightthickness=0, bd=0)

        self.passw_entry = tk.Entry(self.frame, textvariable=secret_var, show='*')

        peek_btn.bind('<Button-1>', self.show_password)
        peek_btn.bind('<ButtonRelease-1>', self.hide_password)
        
        secret_label.grid(row=1,column=0)
        self.passw_entry.grid(row=1,column=1)
        peek_btn.grid(row=1,column=2)

    def show_password(self, e):
        self.passw_entry.config(show='')

    def hide_password(self, e):
        self.passw_entry.config(show='*')