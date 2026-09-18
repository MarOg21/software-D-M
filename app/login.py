"""
UC0 -- Log In.

Admin and Receptionist use similar credentials type. Members receive their credentials automatically when they are registered. A successful
Member login is directly linked to the member ID, so the Member can only view their own membership information.
"""
import tkinter as tk

from data_store import MemberAccountRepository

# Fixed staff/receptionist credential table for the prototype. username -> (password, role)
CREDENTIALS = {
    "admin": ("admin123", "Admin"),
    "receptionist": ("reception123", "Receptionist"),
}


class LoginScreen(tk.Tk):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.member_accounts = MemberAccountRepository() # initializes the member account repository to handle member authentication
        self.title("Gym Membership System -- Log In")
        self.geometry("460x390")
        self.configure(bg="#eef2f7")
        self.resizable(False, False)

        tk.Label(self, text="🏋", bg="#eef2f7", font=("Helvetica", 36)).pack(pady=(30, 0))
        tk.Label(self, text="Gym Membership System", bg="#eef2f7",
                 font=("Helvetica", 14, "bold")).pack(pady=(0, 20))

        form = tk.Frame(self, bg="#eef2f7")
        form.pack()

        tk.Label(form, text="Username:", bg="#eef2f7").grid(row=0, column=0, sticky="e", pady=8, padx=6)
        self.username_var = tk.StringVar()
        tk.Entry(form, textvariable=self.username_var).grid(row=0, column=1, pady=8)

        tk.Label(form, text="Password:", bg="#eef2f7").grid(row=1, column=0, sticky="e", pady=8, padx=6)
        self.password_var = tk.StringVar()
        pw_entry = tk.Entry(form, textvariable=self.password_var, show="*")
        pw_entry.grid(row=1, column=1, pady=8)
        pw_entry.bind("<Return>", lambda e: self.do_login())

        tk.Button(self, text="Log In", command=self.do_login,
                  bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
                  relief="flat", cursor="hand2", font=("Helvetica", 11, "bold"),
                  padx=28, pady=8).pack(pady=18)

        self.error_label = tk.Label(self, text="", bg="#eef2f7", fg="#c62828", font=("Helvetica", 9))
        self.error_label.pack()

        tk.Label(self,
                 text="Staff demo: admin/admin123 or receptionist/reception123\nMembers use the credentials issued at registration.",
                 bg="#eef2f7", fg="#888", font=("Helvetica", 8), justify="center").pack(side="bottom", pady=10)

    def do_login(self):
        username = self.username_var.get().strip() # Get the username from the input field and remove any leading/trailing whitespace
        password = self.password_var.get()

        # so first checks if the log in credentials match any staff/receptionist accounts.
        entry = CREDENTIALS.get(username)
        if entry is not None and entry[0] == password: #checks the entry in the CREDENTIALS dictionary for the given username and compares the password. If they match, it retrieves the role associated with that username.
            role = entry[1]
            self.destroy()
            self.on_success(role, None)
            return

        # Then checks Member accounts.
        member_account = self.member_accounts.authenticate(username, password)
        if member_account:
            self.destroy()
            self.on_success("Member", member_account["member_id"])
            return
        # if neither staff/receptionist nor member credentials match, it displays an error message indicating that the username or password is invalid.
        self.error_label.config(text="⚠ Invalid username or password.")
