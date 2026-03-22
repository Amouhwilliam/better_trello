from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from domain.models.project import Project


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, examples=["Q2 Product Launch"])
    deadline: datetime = Field(..., examples=["2026-06-30T23:59:59Z"])


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    deadline: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    deadline: datetime
    completed: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectResponse":
        return cls(
            id=project.id,
            title=project.title,
            deadline=project.deadline,
            completed=project.completed,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
