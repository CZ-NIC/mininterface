import tkinter as tk
 
root=tk.Tk()

secret_var=tk.StringVar()

secret_label = tk.Label(root, text = 'Secret')
 
def show_password(e):
    passw_entry.config(show='')

def hide_password(e):
    passw_entry.config(show='*')

icon = tk.PhotoImage(file="../../asset/eye.png", width=25, height=25)

passw_entry = tk.Entry(root, textvariable=secret_var, show='*')

peek_btn = tk.Button(root, text='Peek', image=icon, width=25, height=25, highlightthickness=0, bd=0, highlightbackground=None)
peek_btn.bind('<Button-1>', show_password)
peek_btn.bind('<ButtonRelease-1>', hide_password)
 
secret_label.grid(row=1,column=0)
passw_entry.grid(row=1,column=1)
peek_btn.grid(row=1,column=2)
 
root.mainloop()
