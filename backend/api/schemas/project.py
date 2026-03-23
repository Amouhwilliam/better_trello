from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from domain.models.project import Project


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, examples=["Q2 Product Launch"])
    deadline: datetime = Field(..., examples=["2026-06-30T23:59:59Z"])
    owner_id: Optional[UUID] = Field(None, examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    deadline: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    deadline: datetime
    completed: bool
    owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls(
            id=project.id,
            title=project.title,
            deadline=project.deadline,
            completed=project.completed,
            owner_id=project.owner_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
