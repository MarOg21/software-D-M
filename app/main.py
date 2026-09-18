"""
Gym Membership Management System -- Desktop Application (Tkinter)

This is the APP layer. Verification is performed through MembershipVerifier
(the library facade). The app configures that facade with reusable rule
strategies and supplies an app-side repository adapter.
"""
import os
import sys
import secrets
import re
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "library"))
from checkin_verification import (
    ActiveStatusRule,
    DuplicateCheckRule,
    GuestPassQuotaRule,
    HoursRule,
    Member,
    MembershipStatus,
    MembershipVerifier,
    TierAccessRule,
)

from data_store import CheckInLog, JsonMemberRepository, MemberAccountRepository, PlanRepository

DEFAULT_GUEST_PASSES = 3 # This initialises the guest pass number.

STATUS_COLORS = {
    MembershipStatus.ACTIVE: "#2e7d32",
    MembershipStatus.FROZEN: "#1565c0",
    MembershipStatus.EXPIRED: "#c62828",
    MembershipStatus.PENDING_ACTIVATION: "#ef6c00",
    MembershipStatus.CANCELLED: "#c62828",
} # This maps membership statuses to colors for better UI display.


def add_months(start: date, months: int) -> date:
    """This function adds the whole calendar months to avoid assuming every month has 30 days, for accuracy."""
    import calendar
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class GymApp(tk.Tk):
    def __init__(self, role: str = "Admin", member_id: str = None):
        super().__init__()
        self.role = role  # "Admin", "Receptionist", or "Member". set by UC0 Log In
        self.member_id = member_id  # If role is "Member", this is the member's ID, set by UC0 Log In
        self.title(f"Gym Membership Management System -- logged in as {role}")
        self.geometry("1100x720")
        self.minsize(980, 650)
        self.configure(bg="#eef2f7")
        self._configure_styles()

        # This is the App layer objects 
        self.repository = JsonMemberRepository()
        self.log = CheckInLog()
        self.plans = PlanRepository()
        self.member_accounts = MemberAccountRepository()

        #Library facade: The single entry point used to execute verification
        self.verifier = self._build_verifier()

        # A second facade instance, same class, different rule pipeline
        # This is the UC7's verification aspect: "is this member allowed to issue a guest pass?"
        self.guest_pass_verifier = MembershipVerifier(
            rules=[ActiveStatusRule(), GuestPassQuotaRule()],
            repository=self.repository,
        )

        self._build_ui()

    def _configure_styles(self):
        """This applies a consistent modern ttk theme across the desktop UI."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background="#eef2f7", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", "#1d4ed8")])
        style.configure("Treeview", rowheight=30, font=("Helvetica", 10), fieldbackground="white", background="white")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), padding=7)
        style.configure("TCombobox", padding=5)

    def _build_verifier(self) -> MembershipVerifier:
        """This re-builds the check-in verifier using the CURRENT plans (UC4),
        so all changes made by an Admin related to plan and tier, take effect immediately --
        this is what ties UC4 to UC1 in a real, functioning way."""
        return MembershipVerifier(
            rules=[
                ActiveStatusRule(),
                TierAccessRule(tier_hierarchy=self.plans.tier_hierarchy()),
                HoursRule(open_hour=0, close_hour=24),  # This is open 24h for demo purposes
                DuplicateCheckRule(),  # cooldown time
            ],
            repository=self.repository,
        )

    def rebuild_verifier(self):
        """Called by ManagePlansTab whenever plans changes because of the admin."""
        self.verifier = self._build_verifier()

    # ------------------------------------------------------------------
    def _build_ui(self):
        header = tk.Frame(self, bg="#1f2937", height=60)
        header.pack(fill="x")
        tk.Label(header, text="🏋  Gym Membership Management System", bg="#1f2937",
                 fg="white", font=("Helvetica", 16, "bold")).pack(side="left", padx=20, pady=14)
        role_text = f"Role: {self.role}"
        if self.role == "Member" and self.member_id:
            role_text += f"  |  Member ID: {self.member_id}"
        tk.Label(header, text=role_text, bg="#1f2937", fg="#93c5fd",
                 font=("Helvetica", 10, "bold")).pack(side="right", padx=20)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Member self-service is isolated from staff/admin functions.
        if self.role == "Member":
            self.checkin_tab = None
            self.register_tab = None
            self.renew_tab = None
            self.guest_pass_tab = None
            self.members_tab = None
            self.plans_tab = None
            self.freeze_tab = None
            self.reports_tab = None

            self.my_info_tab = MyInfoTab(notebook, self, self.member_id)
            notebook.add(self.my_info_tab, text="  My Membership  ")
        else:
            # Receptionist tabs (also available to Admin).
            self.checkin_tab = CheckInTab(notebook, self)
            self.register_tab = RegisterTab(notebook, self)
            self.renew_tab = RenewTab(notebook, self)
            self.guest_pass_tab = GuestPassTab(notebook, self)
            self.members_tab = RegisteredMembersTab(notebook, self)
            self.my_info_tab = None

            notebook.add(self.checkin_tab, text="  Check-in  ")
            notebook.add(self.register_tab, text="  Register  ")
            notebook.add(self.renew_tab, text="  Renew  ")
            notebook.add(self.guest_pass_tab, text="  Guest Pass  ")
            notebook.add(self.members_tab, text="  Registered Members  ")

            # This is the Admin-only tabs.
            if self.role == "Admin":
                self.plans_tab = ManagePlansTab(notebook, self)
                self.freeze_tab = FreezeTab(notebook, self)
                self.reports_tab = ReportsTab(notebook, self)
                notebook.add(self.plans_tab, text="  Manage Plans  ")
                notebook.add(self.freeze_tab, text="  Freeze/Suspend  ")
                notebook.add(self.reports_tab, text="  Reports  ")
            else:
                self.plans_tab = None
                self.freeze_tab = None
                self.reports_tab = None

        self.notebook = notebook
    # ------------------------------------------------------------------
    def refresh_all(self):
        if self.freeze_tab:
            self.freeze_tab.refresh_list()
        if self.reports_tab:
            self.reports_tab.refresh_list()
        if self.guest_pass_tab:
            self.guest_pass_tab.refresh_list()
        if self.members_tab:
            self.members_tab.refresh_list()
        if self.my_info_tab:
            self.my_info_tab.refresh_info()

    def refresh_tier_dropdowns(self):
        """This is called after UC4 plan changes so other tabs can see new tiers."""
        tier_names = self.plans.tier_names()
        if self.checkin_tab:
            self.checkin_tab.tier_combo["values"] = tier_names
        if self.register_tab:
            self.register_tab.tier_combo["values"] = tier_names
        if self.renew_tab:
            self.renew_tab.plan_combo["values"] = tier_names


# ==========================================================================
class CheckInTab(tk.Frame):
    """UC1 -- the core use case. Talks only to app.verifier.verify()."""

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        tk.Label(self, text="Scan / Enter Member ID", bg="white",
                  font=("Helvetica", 13, "bold")).pack(pady=(24, 6))

        entry_frame = tk.Frame(self, bg="white")
        entry_frame.pack(pady=6)
        self.member_id_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self.member_id_var, font=("Helvetica", 14), width=20)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self.do_check_in())
        tk.Button(entry_frame, text="Check In", command=self.do_check_in,
                  bg="#2563eb", fg="white", font=("Helvetica", 11, "bold"), padx=14).pack(side="left")

        tk.Label(self, text="Required facility tier for this check-in:", bg="white",
                  font=("Helvetica", 10)).pack(pady=(18, 2))
        self.tier_var = tk.StringVar(value="Basic")
        self.tier_combo = ttk.Combobox(self, textvariable=self.tier_var,
                                        values=self.app.plans.tier_names(),
                                        state="readonly", width=15)
        self.tier_combo.pack()

        self.result_frame = tk.Frame(self, bg="white")
        self.result_frame.pack(pady=30, fill="x")

        self.result_label = tk.Label(self.result_frame, text="", bg="white",
                                      font=("Helvetica", 20, "bold"))
        self.result_label.pack()
        self.detail_label = tk.Label(self.result_frame, text="", bg="white",
                                      font=("Helvetica", 11))
        self.detail_label.pack(pady=4)

        tk.Label(self, text="Try: M001 (active), M002 (expired), M003 (frozen), M005 (pending)",
                  bg="white", fg="#888", font=("Helvetica", 9)).pack(side="bottom", pady=10)

    def do_check_in(self):
        member_id = self.member_id_var.get().strip()
        if not member_id:
            return
        timestamp = datetime.now()
        context = {"required_tier": self.tier_var.get()}

        #The single call into the library facade (mirrors the sequence diagram)
        result = self.app.verifier.verify(member_id, timestamp=timestamp, context=context)

        member_name = result.member.name if result.member else member_id
        self.app.log.record_check_in(member_id, member_name, result.allowed,
                                      result.reason_code, result.message, timestamp)

        if result.allowed:
            self.result_label.config(text=f"✅ ACCESS GRANTED", fg="#2e7d32")
            self.detail_label.config(text=f"Welcome, {member_name}!")
            if result.member:
                result.member.last_check_in = timestamp
                self.app.repository.save_member(result.member)
        else:
            self.result_label.config(text=f"⛔ ACCESS DENIED", fg="#c62828")
            self.detail_label.config(text=f"{member_name}: {result.message}  [{result.reason_code}]")

        self.member_id_var.set("")
        self.app.refresh_all()


# ==========================================================================
class RegisterTab(tk.Frame):
    """UC2 -- Register New Member."""

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        form = tk.Frame(self, bg="white")
        form.pack(pady=30)

        tk.Label(form, text="Register New Member", bg="white",
                  font=("Helvetica", 13, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 16))

        tk.Label(form, text="Name:", bg="white").grid(row=1, column=0, sticky="e", pady=6, padx=6)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var).grid(row=1, column=1, pady=6)

        tk.Label(form, text="Email Address:", bg="white").grid(row=2, column=0, sticky="e", pady=6, padx=6)
        self.email_var = tk.StringVar()
        tk.Entry(form, textvariable=self.email_var, width=28).grid(row=2, column=1, pady=6)

        tk.Label(form, text="Phone Number:", bg="white").grid(row=3, column=0, sticky="e", pady=6, padx=6)
        self.phone_var = tk.StringVar()
        tk.Entry(form, textvariable=self.phone_var, width=28).grid(row=3, column=1, pady=6)

        tk.Label(form, text="Tier:", bg="white").grid(row=4, column=0, sticky="e", pady=6, padx=6)
        self.tier_var = tk.StringVar(value="Basic")
        self.tier_combo = ttk.Combobox(form, textvariable=self.tier_var,
                                        values=app.plans.tier_names(), state="readonly", width=25)
        self.tier_combo.grid(row=4, column=1, pady=6)

        tk.Button(form, text="Register Member", command=self.do_register,
                  bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white",
                  relief="flat", cursor="hand2", font=("Helvetica", 11, "bold"),
                  padx=18, pady=7).grid(row=5, column=0, columnspan=2, pady=18)

        self.status_label = tk.Label(self, text="", bg="white", font=("Helvetica", 10))
        self.status_label.pack()

    def do_register(self):
        name = self.name_var.get().strip()
        email = self.email_var.get().strip()
        phone = self.phone_var.get().strip()
        if not name:
            self.status_label.config(text="⚠ Name is required.", fg="#c62828")
            return
        if not email:
            self.status_label.config(text="⚠ Email address is required.", fg="#c62828")
            return
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            self.status_label.config(text="⚠ Enter a valid email address.", fg="#c62828")
            return
        if phone and not re.fullmatch(r"[+0-9 ()-]{6,20}", phone):
            self.status_label.config(text="⚠ Enter a valid phone number.", fg="#c62828")
            return
        # This Check for duplicate email / phone, to avoid same contact registered twice
        owned_email = email.lower()
        owned_phone = phone
        for existing_member in self.app.repository.all_members():
            existing_email = (getattr(existing_member, "email", "") or "").strip().lower()
            existing_phone = (getattr(existing_member, "phone", "") or "").strip()

            if existing_email == owned_email:
                self.status_label.config(
                    text="⚠ A member with this email address already exists, Please use a different email.",
                    fg="#C62828"
                )
                return

            if owned_phone and existing_phone == owned_phone:
                self.status_label.config(
                    text="⚠ A member with this phone number already exists, Please use a different number.",
                    fg="#C62828"
                )
                return

        # Assigned automatically
        member_id = self.app.repository.next_member_id()

        new_member = Member(
            member_id=member_id, name=name, tier=self.tier_var.get(),
            status=MembershipStatus.PENDING_ACTIVATION, email=email, phone=phone,
            expiry_date=None,  # not assigned until payment is confirmed (UC3)
            guest_passes_remaining=DEFAULT_GUEST_PASSES,
        )
        self.app.repository.save_member(new_member)

        # Create a login account linked to this exact member. The member ID is 
        # used as the username and a temporary password is generated for the demo.
        username = member_id
        temporary_password = "GF" + str(secrets.randbelow(900000) + 100000)
        self.app.member_accounts.create_account(member_id, username, temporary_password)

        self.status_label.config(
            text=(f"✅ {name} registered as {member_id} (PendingActivation).\n"
                  f"Member login -> Username: {username}   Temporary password: {temporary_password}"),
            fg="#2e7d32"
        )
        self.name_var.set("")
        self.email_var.set("")
        self.phone_var.set("")
        self.app.refresh_all()


# ==========================================================================
class RenewTab(tk.Frame):
    """UC3 -- Activate or renew a membership after plan/duration selection.

    The receptionist selects the membership plan and duration, the system
    calculates the total price and expiry date, and payment confirmation
    activates the membership.
    """

    DURATIONS = (1, 3, 6, 12)

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        form = tk.Frame(self, bg="white")
        form.pack(pady=24)

        tk.Label(form, text="Activate / Renew Membership", bg="white",
                 font=("Helvetica", 13, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 16))

        tk.Label(form, text="Member ID:", bg="white").grid(row=1, column=0, sticky="e", pady=6, padx=6)
        self.id_var = tk.StringVar()
        tk.Entry(form, textvariable=self.id_var).grid(row=1, column=1, pady=6, sticky="w")

        tk.Label(form, text="Membership Plan:", bg="white").grid(row=2, column=0, sticky="e", pady=6, padx=6)
        default_plan = app.plans.tier_names()[0] if app.plans.tier_names() else ""
        self.plan_var = tk.StringVar(value=default_plan)
        self.plan_combo = ttk.Combobox(
            form, textvariable=self.plan_var, values=app.plans.tier_names(),
            state="readonly", width=18
        )
        self.plan_combo.grid(row=2, column=1, pady=6, sticky="w")
        self.plan_combo.bind("<<ComboboxSelected>>", lambda e: self.update_price_preview())

        tk.Label(form, text="Duration:", bg="white").grid(row=3, column=0, sticky="e", pady=6, padx=6)
        self.duration_var = tk.StringVar(value="12")
        self.duration_combo = ttk.Combobox(
            form, textvariable=self.duration_var,
            values=[str(m) for m in self.DURATIONS], state="readonly", width=18
        )
        self.duration_combo.grid(row=3, column=1, pady=6, sticky="w")
        self.duration_combo.bind("<<ComboboxSelected>>", lambda e: self.update_price_preview())

        self.price_label = tk.Label(form, text="", bg="white", fg="#374151",
                                    font=("Helvetica", 10, "bold"))
        self.price_label.grid(row=4, column=0, columnspan=2, pady=(8, 2))

        tk.Button(form, text="Confirm Payment & Activate / Renew", command=self.do_renew,
                  bg="#2563eb", fg="white", font=("Helvetica", 11, "bold"),
                  padx=14).grid(row=5, column=0, columnspan=2, pady=18)

        self.status_label = tk.Label(self, text="", bg="white", font=("Helvetica", 10))
        self.status_label.pack()
        self.update_price_preview()

    def update_price_preview(self):
        plan = self.app.plans.get_plan(self.plan_var.get())
        if not plan:
            self.price_label.config(text="Select a valid membership plan.")
            return
        months = int(self.duration_var.get())
        monthly_price = float(plan["price"])
        total = monthly_price * months
        self.price_label.config(
            text=f"{plan['name']}: ${monthly_price:.2f}/month × {months} month(s) = ${total:.2f}"
        )

    def do_renew(self):
        member_id = self.id_var.get().strip()
        member = self.app.repository.get_member(member_id)
        if not member:
            self.status_label.config(text="⚠ Member not found.", fg="#c62828")
            return

        # Cancelled is a terminal state in the statechart.
        if member.status == MembershipStatus.CANCELLED:
            self.status_label.config(
                text="⛔ Cancelled memberships cannot be renewed or reactivated.", fg="#c62828"
            )
            return

        plan = self.app.plans.get_plan(self.plan_var.get())
        if not plan:
            self.status_label.config(text="⚠ Select a valid membership plan.", fg="#c62828")
            return

        try:
            months = int(self.duration_var.get())
        except ValueError:
            self.status_label.config(text="⚠ Select a valid membership duration.", fg="#c62828")
            return
        if months not in self.DURATIONS:
            self.status_label.config(text="⚠ Unsupported membership duration.", fg="#c62828")
            return

        monthly_price = float(plan["price"])
        total_price = monthly_price * months

        # If an active membership still has time left, extend from its current
        # expiry date. Otherwise activation/renewal starts today.
        today = date.today()
        base_date = member.expiry_date if (
            member.status == MembershipStatus.ACTIVE
            and member.expiry_date is not None
            and member.expiry_date >= today
        ) else today

        member.tier = plan["name"]
        member.status = MembershipStatus.ACTIVE
        member.expiry_date = add_months(base_date, months)
        # Every activated/renewed membership starts the new period with 3 guest passes.
        member.guest_passes_remaining = DEFAULT_GUEST_PASSES
        self.app.repository.save_member(member)

        self.status_label.config(
            text=(f"✅ Payment confirmed: ${total_price:.2f}. {member.name} -> {plan['name']} "
                  f"for {months} month(s), active until {member.expiry_date}."),
            fg="#2e7d32"
        )
        self.id_var.set("")
        self.app.refresh_all()


# ==========================================================================
# handles Logic for UC6 -- Freeze / Unfreeze Membership
class FreezeTab(tk.Frame):
    """UC6 -- Freeze / Unfreeze Membership."""

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        top = tk.Frame(self, bg="white")
        top.pack(pady=16)
        tk.Label(top, text="Member ID:", bg="white").pack(side="left", padx=6)
        self.id_var = tk.StringVar()
        tk.Entry(top, textvariable=self.id_var, width=15).pack(side="left", padx=6)
        tk.Button(top, text="Freeze", command=self.do_freeze,
                  bg="#1565c0", fg="white", padx=10).pack(side="left", padx=4)
        tk.Button(top, text="Unfreeze", command=self.do_unfreeze,
                  bg="#2e7d32", fg="white", padx=10).pack(side="left", padx=4)
        tk.Button(top, text="Cancel Membership", command=self.do_cancel,
                  bg="#c62828", fg="white", padx=10).pack(side="left", padx=4)

        self.tree = ttk.Treeview(self, columns=("id", "name", "tier", "status", "expiry"),
                                  show="headings", height=14)
        for col, label, width in [("id", "Member ID", 90), ("name", "Name", 160),
                                   ("tier", "Tier", 90), ("status", "Status", 140),
                                   ("expiry", "Expiry", 100)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=16, pady=10)

        self.refresh_list()

    def do_freeze(self):
        member_id = self.id_var.get().strip()
        member = self.app.repository.get_member(member_id)
        if not member:
            messagebox.showwarning("Not found", f"There exist no member with ID '{member_id}'.")
            return
        if member.status == MembershipStatus.CANCELLED:
            messagebox.showwarning("Cancelled membership", "Cancelled memberships cannot change state.")
            return
        if member.status != MembershipStatus.ACTIVE:
            messagebox.showwarning("Cannot freeze", "Only an active membership can be frozen/suspended.")
            return
        self._set_status(MembershipStatus.FROZEN)

    def do_unfreeze(self):
        member_id = self.id_var.get().strip()
        member = self.app.repository.get_member(member_id)
        if not member:
            messagebox.showwarning("Not found", f"There exist no member with ID '{member_id}'.")
            return
        if member.status == MembershipStatus.CANCELLED:
            messagebox.showwarning("Cancelled membership", "Cancelled memberships cannot be reactivated.")
            return
        if member.status != MembershipStatus.FROZEN:
            messagebox.showwarning("Cannot unfreeze", "Only a frozen/suspended membership can be unfrozen.")
            return
        if member.expiry_date is not None and member.expiry_date < date.today():
            messagebox.showwarning("Membership expired", "This membership expired while frozen. Please renew it instead.")
            return
        self._set_status(MembershipStatus.ACTIVE)

    def do_cancel(self):
        member_id = self.id_var.get().strip()
        member = self.app.repository.get_member(member_id)
        if not member:
            messagebox.showwarning("Not found", f"There exist no member with ID '{member_id}'.")
            return
        confirmed = messagebox.askyesno( # asks the user to confirm cancellation
            "Confirm Cancellation",
            f"Cancel {member.name}'s membership permanently?\n\n"
            f"This is a terminal state -- it cannot be reversed by Freeze/Unfreeze or Renew."
        )
        if confirmed:
            self._set_status(MembershipStatus.CANCELLED)

    def _set_status(self, status: MembershipStatus):
        member_id = self.id_var.get().strip()
        member = self.app.repository.get_member(member_id)
        if not member:
            messagebox.showwarning("Not found", f"There exist no member with ID '{member_id}'.")
            return
        if member.status == MembershipStatus.CANCELLED and status != MembershipStatus.CANCELLED:
            messagebox.showwarning(
                "Cancelled membership",
                "A cancelled membership is a terminal state and cannot be frozen, unfrozen, or reactivated."
            )
            return
        member.status = status # updates the member's status to the new status
        self.app.repository.save_member(member) # saves the updated member status to the repository
        self.id_var.set("")
        self.app.refresh_all()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children()) # delets all existing entries in the treeview
        for m in self.app.repository.all_members(): # iterates through all members in the repository
            self.tree.insert("", "end", values=(m.member_id, m.name, m.tier, m.status.value,
                                                  m.expiry_date if m.expiry_date else "Not activated")) # inserts the member's information into the treeview


# ==========================================================================
class GuestPassTab(tk.Frame): 
    'Uses UC7 -- Issue Guest Pass. Receptionist can issue a guest pass to a member if they have any remaining.'

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        tk.Label(self, text="Issue Guest Pass", bg="white",
                  font=("Helvetica", 13, "bold")).pack(pady=(20, 10))

        entry_frame = tk.Frame(self, bg="white")
        entry_frame.pack(pady=6)
        tk.Label(entry_frame, text="Sponsoring Member ID:", bg="white").pack(side="left", padx=6)
        self.id_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self.id_var, width=15)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self.do_issue())
        tk.Button(entry_frame, text="Issue Guest Pass", command=self.do_issue,
                  bg="#2563eb", fg="white", font=("Helvetica", 10, "bold"), padx=10).pack(side="left")

        self.status_label = tk.Label(self, text="", bg="white", font=("Helvetica", 11, "bold"))
        self.status_label.pack(pady=16)

        tk.Label(self, text="Members and remaining guest passes:", bg="white",
                  font=("Helvetica", 10)).pack(pady=(10, 4))
        self.tree = ttk.Treeview(self, columns=("id", "name", "passes"),
                                  show="headings", height=10)
        for col, label, width in [("id", "Member ID", 100), ("name", "Name", 180),
                                   ("passes", "Guest Passes Left", 140)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(padx=16, pady=6)

        self.refresh_list()

    def do_issue(self):
        member_id = self.id_var.get().strip()
        if not member_id:
            return

        #Same method class as check-in, different rule pipeline
        result = self.app.guest_pass_verifier.verify(member_id) # verifies if the member is allowed to issue a guest pass using the guest_pass_verifier

        if result.allowed:
            member = result.member
            member.guest_passes_remaining -= 1 # subtracts 1 from the member's remaining guest passes
            self.app.repository.save_member(member)
            self.status_label.config(
                text=f"✅ Guest pass has been issued for {member.name}. "
                     f"{member.guest_passes_remaining} remaining this period.",
                fg="#2e7d32")
        else:
            name = result.member.name if result.member else member_id
            self.status_label.config(
                text=f"⛔ Denied for {name}: {result.message}",
                fg="#c62828")

        self.id_var.set("")
        self.app.refresh_all()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for m in self.app.repository.all_members():
            self.tree.insert("", "end", values=(m.member_id, m.name, m.guest_passes_remaining))


# ==========================================================================
class ManagePlansTab(tk.Frame):
    """UC4 -- Manage Membership Plans. (Admin only)"""


    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        tk.Label(self, text="Manage Membership Plans", bg="white",
                  font=("Helvetica", 13, "bold")).pack(pady=(16, 10))

        form = tk.Frame(self, bg="white")
        form.pack(pady=6)

        tk.Label(form, text="Plan Name:", bg="white").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, width=16).grid(row=0, column=1, pady=4)

        tk.Label(form, text="Rank (higher = more access):", bg="white").grid(row=0, column=2, sticky="e", padx=6)
        self.rank_var = tk.StringVar(value="1")
        tk.Entry(form, textvariable=self.rank_var, width=6).grid(row=0, column=3, pady=4)

        tk.Label(form, text="Price ($/mo):", bg="white").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.price_var = tk.StringVar(value="25")
        tk.Entry(form, textvariable=self.price_var, width=16).grid(row=1, column=1, pady=4)

        tk.Label(form, text="Guest Passes / period:", bg="white").grid(row=1, column=2, sticky="e", padx=6)
        self.gp_var = tk.StringVar(value=str(DEFAULT_GUEST_PASSES))
        ttk.Entry(form, textvariable=self.gp_var, width=6, state="readonly").grid(row=1, column=3, pady=4)

        tk.Label(form, text="Description:", bg="white").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        self.desc_var = tk.StringVar()
        tk.Entry(form, textvariable=self.desc_var, width=40).grid(row=2, column=1, columnspan=3, sticky="w", pady=4)

        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Save / Update Plan", command=self.do_save,
                  bg="#2563eb", fg="white", font=("Helvetica", 10, "bold"), padx=12).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Delete Selected Plan", command=self.do_delete,
                  bg="#c62828", fg="white", padx=12).pack(side="left", padx=4)

        self.status_label = tk.Label(self, text="", bg="white", font=("Helvetica", 9))
        self.status_label.pack()

        self.tree = ttk.Treeview(self, columns=("name", "rank", "price", "gp", "desc"),
                                  show="headings", height=8)
        for col, label, width in [("name", "Plan", 100), ("rank", "Rank", 60),
                                   ("price", "Price", 80), ("gp", "Guest Passes", 100),
                                   ("desc", "Description", 300)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, padx=16, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.refresh_list()

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.name_var.set(values[0])
        self.rank_var.set(values[1])
        self.price_var.set(values[2])
        self.gp_var.set(str(DEFAULT_GUEST_PASSES))
        self.desc_var.set(values[4])

    def do_save(self):
        name = self.name_var.get().strip()
        if not name:
            self.status_label.config(text="⚠ Plan name is required.", fg="#c62828")
            return
        try:
            rank = int(self.rank_var.get())
            price = float(self.price_var.get()) # converts the rank and price input values to integer and float respectively
        except ValueError:
            self.status_label.config(text="⚠ Rank and Price must be numeric.", fg="#c62828")
            return

        plan = {"name": name, "rank": rank, "price": price,
                "guest_pass_allowance": DEFAULT_GUEST_PASSES,
                "description": self.desc_var.get().strip()}
        self.app.plans.save_plan(plan)
        self.app.rebuild_verifier() # rebuilds the check-in verifier to reflect the updated plan rules
        self.app.refresh_tier_dropdowns() # refreshes the tier dropdowns in the operational tabs to reflect the updated plan names
        self.status_label.config(text=f"✅ Plan '{name}' saved. Check-in rules updated immediately.", fg="#2e7d32")
        self.refresh_list()

    def do_delete(self):
        name = self.name_var.get().strip()
        if not name:
            return
        if self.app.plans.delete_plan(name): # deletes the plan with the specified name from the plans repository
            self.app.rebuild_verifier()
            self.app.refresh_tier_dropdowns()
            self.status_label.config(text=f"🗑 Plan '{name}' deleted.", fg="#616161")
            self.refresh_list()
        else:
            self.status_label.config(text=f"⚠ Plan '{name}' not found.", fg="#c62828")

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for p in self.app.plans.all_plans():
            self.tree.insert("", "end", values=(p["name"], p["rank"], p["price"],
                                                  p["guest_pass_allowance"], p["description"]))


# ==========================================================================
class RegisteredMembersTab(tk.Frame):
    """Shared Admin/Receptionist view of all registered members."""

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        tk.Label(self, text="Registered Members", bg="white", fg="#111827",
                 font=("Helvetica", 16, "bold")).pack(pady=(18, 4))
        tk.Label(self, text="Member contact details, plan and current membership status.",
                 bg="white", fg="#6b7280", font=("Helvetica", 9)).pack(pady=(0, 10))

        self.tree = ttk.Treeview(
            self, columns=("id", "name", "email", "phone", "tier", "status", "expiry", "passes"),
            show="headings", height=16
        )
        for col, label, width in [
            ("id", "Member ID", 80), ("name", "Name", 140),
            ("email", "Email", 190), ("phone", "Phone", 125),
            ("tier", "Plan", 80), ("status", "Status", 125),
            ("expiry", "Expiry", 105), ("passes", "Passes", 65),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="center" if col not in ("name", "email") else "w")

        self.tree.tag_configure("Active", foreground="#15803d")
        self.tree.tag_configure("Frozen", foreground="#1565c0")
        self.tree.tag_configure("Expired", foreground="#c62828")
        self.tree.tag_configure("Cancelled", foreground="#c62828")
        self.tree.tag_configure("PendingActivation", foreground="#ef6c00")
        self.tree.pack(fill="both", expand=True, padx=16, pady=10)

        legend = tk.Label(self, text="● Active   ● Frozen   ● Expired/Cancelled   ● Pending Activation",
                          bg="white", fg="#4b5563", font=("Helvetica", 9, "bold"))
        legend.pack(pady=(0, 6))
        tk.Button(self, text="Refresh List", command=self.refresh_list, bg="#2563eb", fg="white",
                  activebackground="#1d4ed8", activeforeground="white", relief="flat", cursor="hand2",
                  padx=16, pady=6).pack(pady=(0, 12))
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for member in self.app.repository.all_members():
            expiry = member.expiry_date if member.expiry_date else "Pending activation"
            status = member.status.value
            self.tree.insert("", "end", tags=(status,), values=(
                member.member_id, member.name, member.email or "—", member.phone or "—",
                member.tier, status, expiry, member.guest_passes_remaining
            ))


# ==========================================================================
class MyInfoTab(tk.Frame):
    """UC8 -- View My Membership Info for the authenticated Member only."""

    def __init__(self, parent, app: GymApp, member_id: str):
        super().__init__(parent, bg="white")
        self.app = app
        self.member_id = member_id

        tk.Label(self, text="My Membership", bg="white",
                 font=("Helvetica", 13, "bold")).pack(pady=(20, 10))

        self.info_frame = tk.Frame(self, bg="white")
        self.info_frame.pack(pady=16, fill="x", padx=30)

        self.name_label = tk.Label(self.info_frame, text="", bg="white", font=("Helvetica", 15, "bold"))
        self.name_label.pack(anchor="w")
        self.status_label = tk.Label(self.info_frame, text="", bg="white", font=("Helvetica", 12, "bold"))
        self.status_label.pack(anchor="w", pady=(4, 0))
        self.details_label = tk.Label(self.info_frame, text="", bg="white",
                                      font=("Helvetica", 10), justify="left")
        self.details_label.pack(anchor="w", pady=(8, 0))

        tk.Label(self, text="Recent Check-in History:", bg="white",
                 font=("Helvetica", 10, "bold")).pack(anchor="w", padx=30, pady=(10, 4))
        self.tree = ttk.Treeview(self, columns=("time", "result", "reason"),
                                 show="headings", height=6)
        for col, label, width in [("time", "Time", 160), ("result", "Result", 80),
                                  ("reason", "Reason", 300)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.tag_configure("ALLOW", foreground="#2e7d32")
        self.tree.tag_configure("DENY", foreground="#c62828")
        self.tree.pack(padx=30, pady=6, fill="x")

        tk.Button(self, text="Refresh", command=self.refresh_info,
                  bg="#2563eb", fg="white", padx=12).pack(pady=8)
        self.refresh_info()

    def refresh_info(self):
        self.tree.delete(*self.tree.get_children())
        member = self.app.repository.get_member(self.member_id)
        if not member:
            self.name_label.config(text="⚠ Member record not found", fg="#c62828") # displays a warning message if the member record is not found
            self.status_label.config(text="")
            self.details_label.config(text="Please contact the front desk for help.")
            return

        self.name_label.config(text=f"Welcome, {member.name}", fg="#111827")
        color = STATUS_COLORS.get(member.status, "#111827")
        self.status_label.config(text=f"Status: {member.status.value}", fg=color)

        expiry_display = member.expiry_date if member.expiry_date else "Not yet activated (payment pending)"
        # Display the member's information in a formatted string
        details = (
            f"Member ID: {member.member_id}\n"
            f"Email: {member.email or '—'}\n"
            f"Phone: {member.phone or '—'}\n"
            f"Membership Plan: {member.tier}\n"
            f"Expiry Date: {expiry_display}\n"
            f"Guest Passes Remaining: {member.guest_passes_remaining}"
        )
        # Add special messages for certain membership statuses with conditional behaviours
        if member.status == MembershipStatus.PENDING_ACTIVATION:
            details += "\n\n⚠ Your membership is pending payment/activation."
        elif member.status == MembershipStatus.FROZEN:
            details += "\n\n⚠ Your membership is frozen. Contact staff to reactivate."
        elif member.status == MembershipStatus.EXPIRED:
            details += "\n\n⚠ Your membership has expired. Please renew at the front desk."
        elif member.status == MembershipStatus.CANCELLED:
            details += "\n\n⚠ This membership has been cancelled."
        self.details_label.config(text=details)

        for entry in self.app.log.entries_for_member(self.member_id)[:5]:
            ts = entry["timestamp"].replace("T", " ")[:19]
            self.tree.insert("", "end", tags=(entry["result"],),
                             values=(ts, entry["result"], entry["message"]))


# ==========================================================================
class ReportsTab(tk.Frame):
    """UC5 -- View Check-in History / Reports."""

    def __init__(self, parent, app: GymApp):
        super().__init__(parent, bg="white")
        self.app = app

        tk.Label(self, text="Check-in History", bg="white",
                  font=("Helvetica", 13, "bold")).pack(pady=(16, 8))

        self.tree = ttk.Treeview(
            self, columns=("time", "id", "name", "result", "reason"),
            show="headings", height=16)
        for col, label, width in [("time", "Time", 150), ("id", "Member ID", 90),
                                   ("name", "Name", 160), ("result", "Result", 80),
                                   ("reason", "Reason", 220)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.tag_configure("ALLOW", foreground="#2e7d32")
        self.tree.tag_configure("DENY", foreground="#c62828")
        self.tree.pack(fill="both", expand=True, padx=16, pady=10)

        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for entry in self.app.log.all_entries():
            ts = entry["timestamp"].replace("T", " ")[:19]
            self.tree.insert("", "end", tags=(entry["result"],),
                              values=(ts, entry["member_id"], entry["member_name"],
                                      entry["result"], entry["message"]))


def launch_main_app(role: str, member_id: str = None): # launches the main application with the specified role and member ID
    app = GymApp(role=role, member_id=member_id)
    app.mainloop()


if __name__ == "__main__":
    from login import LoginScreen # imports the LoginScreen class from the login module
    login = LoginScreen(on_success=launch_main_app)
    login.mainloop() # starts the login screen and waits for user interaction. Upon successful login, it will call the launch_main_app function with the appropriate role and member ID.
