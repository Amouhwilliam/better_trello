from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from domain.models.user import User


class UserCreate(BaseModel):
    fullname: str = Field(..., min_length=1, examples=["Alice Dupont"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., min_length=6, examples=["s3cr3tpassword"])


class UserUpdate(BaseModel):
    fullname: str | None = Field(None, min_length=1)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6)


class UserResponse(BaseModel):
    id: UUID
    fullname: str
    email: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class PaginatedUsersResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
