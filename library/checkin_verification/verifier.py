"""
MembershipVerifier -- the library's Facade.

This is the ONLY class the app is supposed to talk to. It does not exposethe rule
pipeline and the repository behind one simple method: verify().
"""
from datetime import datetime
from typing import List, Optional

# the . means "from the same package as this file"
# verification_result is a dataclass that holds the result of a verification attempt
# IMemberRepository determines how the verifier gets members.
# IVerificationRule is the interface for rules that can be applied to a member.
from .models import VerificationResult 
from .repository import IMemberRepository
from .rules import IVerificationRule


class MembershipVerifier:
    def __init__(self, rules: List[IVerificationRule], repository: IMemberRepository):
        if not rules: # avoids an empty pipeline, which would always return True and be a security risk.
            raise ValueError("MembershipVerifier requires at least one rule in its pipeline!.")
        self.rules = rules
        self.repository = repository

    def verify(self, member_id: str, timestamp: Optional[datetime] = None,
               context: Optional[dict] = None) -> VerificationResult:
        timestamp = timestamp or datetime.now()
        context = context or {} # use an empty dict if no context is provided

        # looking up repository.
        member = self.repository.get_member(member_id)
        if member is None:
            return VerificationResult(False, "NOT_FOUND", "Member not found.")

        for rule in self.rules:
            result = rule.evaluate(member, timestamp, context)
            if not result.passed:
                return VerificationResult(False, result.reason_code, result.message, member)

        return VerificationResult(True, "", "Access Granted", member)
