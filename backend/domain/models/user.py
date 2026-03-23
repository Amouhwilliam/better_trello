from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class User:
    fullname: str
    email: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, fullname: Optional[str] = None, email: Optional[str] = None) -> None:
        if fullname is not None:
            self.fullname = fullname
        if email is not None:
            self.email = email
        self.updated_at = datetime.now(timezone.utc)

    def update_password(self, new_password_hash: str) -> None:
        self.password_hash = new_password_hash
        self.updated_at = datetime.now(timezone.utc)
