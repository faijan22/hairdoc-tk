from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class VideoProviderError(Exception):
    pass


@dataclass(frozen=True)
class JoinGrant:
    url: str
    expires_at: datetime


class VideoProvider(Protocol):
    code: str

    @property
    def is_configured(self) -> bool: ...

    def create_room(self, *, room_id: str, available_from: datetime, expires_at: datetime) -> None: ...

    def issue_join_grant(
        self, *, room_id: str, user_id: str, user_name: str, is_owner: bool,
        available_from: datetime, expires_at: datetime,
    ) -> JoinGrant: ...

    def close_room(self, *, room_id: str) -> None: ...

