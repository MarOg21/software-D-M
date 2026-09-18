"""
IMemberRepository -- the Adapter pattern boundary.
This is the interface that the MembershipVerifier uses to get member data. The app is expected to provide an implementation of this interface that connects to its own database or data source.
The MembershipVerifier does not care how the data is stored or retrieved, as long as it can
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Member


class IMemberRepository(ABC):
    @abstractmethod
    def get_member(self, member_id: str) -> Optional[Member]:
        raise NotImplementedError

    @abstractmethod
    def save_member(self, member: Member) -> None:
        raise NotImplementedError

    @abstractmethod
    def all_members(self) -> List[Member]:
        raise NotImplementedError
