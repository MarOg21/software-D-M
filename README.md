# GymFlow Gym Management System

GymFlow is a Python/Tkinter desktop application developed for proper managing of gym memberships and all member lifecycles. It contains a reusable `checkin_verification` library that isolates all membership verification rules from the user interface and JSON persistence.

## Features of the system

GymFlow has three major user roles: **Admin, Receptionist and Member**.

- Register a member with name, email and phone number
- Avoid duplicate email/phone during registrations
- Activate and renew memberships
- Check members in daily
- Avoid duplicate check-ins in the same calendar day
- Issue guest passes
- Freeze, suspend and cancel memberships
- Manage all membership plans
- View all registered members and check-in history
- Member login and membership info view

Newly registered members always start as `PENDING_ACTIVATION`. Other related membership states are `ACTIVE`, `FROZEN`, `EXPIRED` and `CANCELLED`.

Each member always receives **3 guest passes per membership period**.

## Reusable Library

This is the reusable library:

```text
library/checkin_verification/
```

It grants membership/access verification independently of the Tkinter UI.

Main components of the verification library:

- `MembershipVerifier` – does verification
- `IVerificationRule` – this is the interface for verification rules
- `ActiveStatusRule`
- `TierAccessRule`
- `HoursRule`
- `DuplicateCheckRule`
- `GuestPassQuotaRule`
- `IMemberRepository` – repository abstraction
- `RuleResult` and `VerificationResult`

The library uses configurable rules, meaning it can be changed and thus allowing the verification mechanism or principles to be reused again with any different applications or persistence implementations.

## Design Patterns Used

GymFlow uses:

- **Strategy Pattern** – This is the implementation of individual verification rules `IVerificationRule`.
- **Facade Pattern** – `MembershipVerifier` This then provides the main verification entry point.
- **Repository/Adapter approach** – `IMemberRepository` This further isolates the reusable library from JSON persistence.

## Project Structure

```text
gym_project/
├── app/
│ ├── main.py
│ ├── login.py
│ └── data_store.py
├── library/
│ └── checkin_verification/
│ ├── models.py
│ ├── repository.py
│ ├── rules.py
│ └── verifier.py
├── data/
└── README.md
```

## Run the Application

From the project directory:

### Windows

```bash
cd gym_project
python app/main.py
```

### macOS/Linux

```bash
cd gym_project
python3 app/main.py
```

## Demo Accounts

**Admins**

```text
Username: admin
Password: admin123
```

**Receptionist**

```text
Username: receptionist
Password: reception123
```

**Member**
```text
username: Member ID
Password: Generated password during registrations
```

## Storage

GymFlow uses JSON files to store all the gym related components and informations like the  member records, plans, accounts and check-in information. JSON was chosen as a lightweight persistence solution for the desktop prototype.

## Tools used

- Python 3
- Tkinter
- JSON
- Git/GitHub