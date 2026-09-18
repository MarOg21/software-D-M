"""
checkin_verification
=====================
This library provides a flexible and extensible framework for verifying gym member check-ins. It uses the Strategy design pattern to allow different verification rules to be applied in a modular way. The MembershipVerifier class serves as the main entry point for the application, orchestrating the evaluation of various rules against a member's data.
The library is designed to be agnostic of the underlying data storage, relying on an abstract repository
"""
from .models import Member, MembershipStatus, RuleResult, VerificationResult
from .repository import IMemberRepository
from .rules import (
    ActiveStatusRule,
    DuplicateCheckRule,
    GuestPassQuotaRule,
    HoursRule,
    IVerificationRule,
    TierAccessRule,
)
from .verifier import MembershipVerifier

__all__ = [
    "Member", "MembershipStatus", "RuleResult", "VerificationResult",
    "IMemberRepository",
    "IVerificationRule", "ActiveStatusRule", "TierAccessRule", "HoursRule",
    "DuplicateCheckRule", "GuestPassQuotaRule",
    "MembershipVerifier",
]
