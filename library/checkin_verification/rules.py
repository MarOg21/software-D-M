"""
Verification rules -- the Strategy pattern in action.
All verification rules implement the IVerificationRule interface, which defines a single method: evaluate().
The MembershipVerifier class uses a list of IVerificationRule instances to evaluate a member's eligibility for check-in. Each rule can return a RuleResult indicating whether the member passes or fails that specific rule. The MembershipVerifier aggregates these results to determine the final outcome of the verification process.
"""

# abc means "Abstract Base Class" -- it's a Python standard library module that lets us define interfaces.
from abc import ABC, abstractmethod
from datetime import datetime

from .models import Member, MembershipStatus, RuleResult


class IVerificationRule(ABC):
    """This is the Strategy interface every rule must implement."""

    @abstractmethod
    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        raise NotImplementedError


class ActiveStatusRule(IVerificationRule):
    """This abruptly denies access when a membership is not currently usable.

    Expiry is validated automatically from expiry_date, so a record cannot
    stay usable just because its stored status still says ACTIVE.
    """

    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        if member.status == MembershipStatus.CANCELLED:
            return RuleResult(False, "CANCELLED", "Membership has been cancelled.")
        if member.status == MembershipStatus.FROZEN:
            return RuleResult(False, "SUSPENDED", "Membership is currently frozen/suspended at the moment.")
        if member.status == MembershipStatus.PENDING_ACTIVATION:
            return RuleResult(False, "PENDING_ACTIVATION", "Membership is pending activation/payment at the moment.")

        # This is an Automatic expiry validattion.
        if member.expiry_date is not None and member.expiry_date < timestamp.date():
            return RuleResult(False, "EXPIRED",
                              f"Membership expired on {member.expiry_date.isoformat()}.")

        # Keep explicit EXPIRED records denied as well.
        if member.status == MembershipStatus.EXPIRED:
            return RuleResult(False, "EXPIRED", "Membership has expired.")

        if member.expiry_date is None:
            return RuleResult(False, "NO_EXPIRY", "Membership has not been activated yet. Please activate your membership before checking in.")

        return RuleResult(True)


class TierAccessRule(IVerificationRule):
    """This checks the member's plan tier and denies check-in if it doesn't cover this facility."""

    DEFAULT_HIERARCHY = {"Basic": 1, "Premium": 2, "Family": 3}

    def __init__(self, tier_hierarchy: dict = None):
        self.tier_hierarchy = tier_hierarchy or self.DEFAULT_HIERARCHY

    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        required_tier = context.get("required_tier", "Basic")
        member_rank = self.tier_hierarchy.get(member.tier, 0)
        required_rank = self.tier_hierarchy.get(required_tier, 0)
        if member_rank < required_rank:
            return RuleResult(False, "TIER_MISMATCH",
                               f"{member.tier} plan does not cover this facility (requires {required_tier}).")
        return RuleResult(True)


class HoursRule(IVerificationRule):
    """This denies check-in outside the facility's allowed hours."""

    def __init__(self, open_hour: int = 6, close_hour: int = 22):
        self.open_hour = open_hour
        self.close_hour = close_hour

    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        hour = timestamp.hour
        if not (self.open_hour <= hour < self.close_hour):
            return RuleResult(False, "OUTSIDE_HOURS",
                               f"Facility is only open {self.open_hour}:00-{self.close_hour}:00.")
        return RuleResult(True)


class DuplicateCheckRule(IVerificationRule):
    """Denies a second check-in on the same calendar day."""

    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        if member.last_check_in and member.last_check_in.date() == timestamp.date():
            return RuleResult(
                False,
                "DUPLICATE",
                "Member has already been checked in today."
            )

        return RuleResult(True)


class GuestPassQuotaRule(IVerificationRule):
    """
    If the member has no guest passes remianing, further guest pass requests will be denied.
    Used by UC7 (Issue Guest Pass) -- This shows the same MembershipVerifier
    facade which was reused with a different rule pipeline for a different check.
    """

    def evaluate(self, member: Member, timestamp: datetime, context: dict) -> RuleResult:
        if member.guest_passes_remaining <= 0:
            return RuleResult(False, "NO_GUEST_PASSES", "No guest passes remaining.")
        return RuleResult(True)
