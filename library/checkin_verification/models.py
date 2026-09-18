"""
Core data models that are used across the check-in verification library.
"""
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class MembershipStatus(Enum):
    PENDING_ACTIVATION = "PendingActivation"
    ACTIVE = "Active"
    FROZEN = "Frozen"
    EXPIRED = "Expired"
    CANCELLED = "Cancelled"


@dataclass
class Member:
    member_id: str
    name: str
    tier: str
    status: MembershipStatus
    email: str = ""
    phone: str = ""
    expiry_date: Optional[date] = None  # unset until payment is confirmed (UC3)
    guest_passes_remaining: int = 3
    last_check_in: Optional[datetime] = None


@dataclass
class RuleResult:
    """Returned just by a single IVerificationRule.evaluate() call."""
    passed: bool
    reason_code: str = ""
    message: str = ""


@dataclass
class VerificationResult:
    """Returned by MembershipVerifier.verify() -- the library's public result type."""
    allowed: bool
    reason_code: str = ""
    message: str = "Access Granted"
    member: Optional[Member] = None
