"""
App-side layer.

JsonMemberRepository uses the library's IMemberRepository interface
(Adapter pattern) -- for the library. it does not matter that data is stored
in a JSON file.

CheckInLog is purely an app-layer concern (not part of the library) --
it keeps record of all check-in and check-in attempt, whether allow or deny, for reporting (UC5).
"""
# json interpretes JSON fies as text, so we need to import the json module to read and write JSON data.
import json
import os
from datetime import date, datetime # handle date and time objects for membership expiry and check-in timestamps
from typing import List, Optional

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "library"))
from checkin_verification import IMemberRepository, Member, MembershipStatus

# defines where the data files are stored, relative to the current file's directory. It constructs the path to the "data" directory and then defines paths for the members.json and checkin_log.json files within that directory.
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MEMBERS_FILE = os.path.join(DATA_DIR, "members.json")
LOG_FILE = os.path.join(DATA_DIR, "checkin_log.json")

# converts a Member object to a dictionary for JSON serialization, including converting date objects to ISO format strings and handling optional fields like expiry_date and last_check_in.
def _member_to_dict(m: Member) -> dict:
    return {
        "member_id": m.member_id,
        "name": m.name,
        "tier": m.tier,
        "expiry_date": m.expiry_date.isoformat() if m.expiry_date else None,
        "status": m.status.value,
        "email": m.email,
        "phone": m.phone,
        "guest_passes_remaining": m.guest_passes_remaining,
        "last_check_in": m.last_check_in.isoformat() if m.last_check_in else None,
    }

# converts json dictionary data back into a Member object, including parsing ISO format strings back into date objects and handling optional fields.
def _member_from_dict(d: dict) -> Member:
    expiry_date = date.fromisoformat(d["expiry_date"]) if d.get("expiry_date") else None
    status = MembershipStatus(d["status"])

    # Automatic expiry valoidation: if a membership is marked as ACTIVE but the expiry date has passed, it is treated as EXPIRED when loaded. This ensures that the system accurately reflects the current status of memberships based on their expiry dates.
    # treated as EXPIRED as soon as it is loaded.
    if status == MembershipStatus.ACTIVE and expiry_date is not None and expiry_date < date.today():
        status = MembershipStatus.EXPIRED

    return Member(
        member_id=d["member_id"],
        name=d["name"],
        tier=d["tier"],
        expiry_date=expiry_date,
        status=status,
        email=d.get("email", ""),
        phone=d.get("phone", ""),
        guest_passes_remaining=d.get("guest_passes_remaining", 3),
        last_check_in=datetime.fromisoformat(d["last_check_in"]) if d.get("last_check_in") else None, # restores members last check in timestamp.
    )

# convert Member objects to dictionaries for JSON serialization.
class JsonMemberRepository(IMemberRepository):

    def __init__(self, path: str = MEMBERS_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True) # ensures that the directory for the data file exists, creating it if necessary. If the file does not exist, it initializes it with an empty list to prepare for storing member records.
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)
    # loads members
    def _load(self) -> List[dict]:
        with open(self.path, "r") as f:
            return json.load(f)
    # saves all member records to the JSON file, overwriting the existing content. It takes a list of dictionaries (representing members) and writes it to the file in a human-readable format with indentation.
    def _save_all(self, records: List[dict]) -> None:
        with open(self.path, "w") as f:
            json.dump(records, f, indent=2) # saves all member records to the JSON file, making it human-readable with indentation for easier inspection and debugging.

    # finding a member by their unique member ID. It iterates through the loaded member records and returns a Member object if a matching ID is found; otherwise, it returns None.
    def get_member(self, member_id: str) -> Optional[Member]:
        for records in self._load():
            if records["member_id"] == member_id:
                return _member_from_dict(records)
        return None
    # saves a Member object to the repository. If a member with the same ID already exists, it updates their record; otherwise, it adds a new record. This method ensures that member data is kept current and consistent in the JSON file.
    def save_member(self, member: Member) -> None:
        records = self._load()
        updated = False
        for i, record in enumerate(records):
            if record["member_id"] == member.member_id:
                records[i] = _member_to_dict(member)
                updated = True
                break
        if not updated:
            records.append(_member_to_dict(member))
        self._save_all(records)
    # get all registered members in the repository, returning a list of Member objects. This allows for easy retrieval and manipulation of all member data within the application.
    def all_members(self) -> List[Member]:
        return [_member_from_dict(records) for records in self._load()]
    
    # generates the next available member ID in the format "M###", where ### is a zero-padded number. It scans existing member IDs to find the highest number and increments it to create a new unique ID for a new member.
    def next_member_id(self) -> str:
        existing = self._load()
        highest = 0
        for records in existing:
            mid = records["member_id"]
            if mid.startswith("M") and mid[1:].isdigit():
                highest = max(highest, int(mid[1:]))
        return f"M{highest + 1:03d}" # if the highest existing member ID is "M005", the next generated ID will be "M006".

# ==========================================================================
# UC5 support: Check-in log (app-layer, not part of the reusable library)
# ==========================================================================
class CheckInLog:
    """This is the app-side storage for check-in attempts (UC5). Not part of the reusable"""
    def __init__(self, path: str = LOG_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)

    def record_check_in(self, member_id: str, member_name: str, allowed: bool,
                         reason_code: str, message: str, timestamp: datetime) -> None:
        entries = self._load()
        entries.append({
            "member_id": member_id,
            "member_name": member_name,
            "result": "ALLOW" if allowed else "DENY",
            "reason_code": reason_code,
            "message": message,
            "timestamp": timestamp.isoformat(),
        })
        with open(self.path, "w") as f:
            json.dump(entries, f, indent=2)

    def _load(self) -> List[dict]:
        with open(self.path, "r") as f:
            return json.load(f)
    # returns all check-in log entries in reverse chronological order (most recent first). This is useful for displaying the latest check-in attempts at the top of a log or report.
    def all_entries(self) -> List[dict]:
        return list(reversed(self._load())) # this method returns all check-in log entries in reverse chronological order (most recent first). This is useful for displaying the latest check-in attempts at the top of a log or report.

    def entries_for_member(self, member_id: str) -> List[dict]:
        return [e for e in self.all_entries() if e["member_id"] == member_id] # this method filters the check-in log entries to return only those associated with a specific member ID. It allows for easy retrieval of a member's check-in history for review or reporting purposes.



# ==========================================================================
# Member self-service
# ==========================================================================
ACCOUNTS_FILE = os.path.join(DATA_DIR, "member_accounts.json") # member accounts stored separately from membership data, allowing for login functionality without exposing sensitive membership information. This separation enhances security and allows for easier management of member accounts.


class MemberAccountRepository:
    """This stores member login accounts separately from membership data.

    Each account is linked to exactly one member_id onlyand Staff/Admin demo accounts
    remain fixed in login.py; this repository is created only for Member accounts.
    """

    def __init__(self, path: str = ACCOUNTS_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)

    def _load(self) -> List[dict]:
        with open(self.path, "r") as f:
            return json.load(f)

    def _save_all(self, records: List[dict]) -> None:
        with open(self.path, "w") as f:
            json.dump(records, f, indent=2)

    def create_account(self, member_id: str, username: str, password: str) -> None:
        records = self._load()
        records = [r for r in records if r.get("member_id") != member_id] # ensures that each member can have only one account. If an account already exists for the given member_id, it is removed before creating a new one. This prevents duplicate accounts for the same member and maintains data integrity.
        records.append({
            "member_id": member_id,
            "username": username,
            "password": password,
            "role": "Member",
        }) # creates the account with the provided member_id, username, password, and a fixed role of "Member". This role designation is important for access control and permissions within the application.
        self._save_all(records)

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        for record in self._load():
            if record.get("username") == username and record.get("password") == password: # if both match.
                return record
        return None

    def get_for_member(self, member_id: str) -> Optional[dict]:
        for record in self._load():
            if record.get("member_id") == member_id: # seraches with a member ID and if the member_id matches, return the account record for that member. This allows for retrieval of account details based on the associated member ID, facilitating account management and user-specific operations.
                return record
        return None

# ==========================================================================
# UC4 support: Membership Plans 
# ==========================================================================
PLANS_FILE = os.path.join(DATA_DIR, "plans.json")

DEFAULT_PLANS = [
    {"name": "Basic", "rank": 1, "price": 35.0, "guest_pass_allowance": 3,
     "description": "Gym floor access only."},
    {"name": "Premium", "rank": 2, "price": 55.0, "guest_pass_allowance": 3,
     "description": "Gym floor + classes + pool."},
    {"name": "Family", "rank": 3, "price": 65.0, "guest_pass_allowance": 3,
     "description": "All facilities, up to 4 family members."},
]


class PlanRepository:
    """App-side storage for membership plans (UC4). Manages membership plans."""

    def __init__(self, path: str = PLANS_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(DEFAULT_PLANS, f, indent=2) # if plans.json does not exist.

    def _load(self) -> List[dict]:
        with open(self.path, "r") as f:
            return json.load(f)
    
    def _save_all(self, plans: List[dict]) -> None:
        with open(self.path, "w") as f:
            json.dump(plans, f, indent=2)
    # returns all plans. Basic, Premium, Family.
    def all_plans(self) -> List[dict]:
        return self._load()
    # finding a plan by its name. It iterates through the loaded plans and returns the plan dictionary if a matching name is found; otherwise, it returns None. This allows for easy retrieval of specific membership plan details based on the plan name.
    def get_plan(self, name: str) -> Optional[dict]:
        for p in self._load():
            if p["name"] == name:
                return p
        return None

    def save_plan(self, plan: dict) -> None:
        plans = self._load()
        for i, p in enumerate(plans):
            if p["name"] == plan["name"]:
                plans[i] = plan
                self._save_all(plans)
                return
        plans.append(plan)
        self._save_all(plans)

    def delete_plan(self, name: str) -> bool:
        plans = self._load()
        remaining = [p for p in plans if p["name"] != name]
        if len(remaining) == len(plans):
            return False
        self._save_all(remaining)
        return True

    def tier_hierarchy(self) -> dict:
        """This builds the {tier_name: rank} dict that TierAccessRule needs from whichever plans currently exist."""
        return {p["name"]: p["rank"] for p in self._load()}

    def tier_names(self) -> List[str]:
        return [p["name"] for p in self._load()]
