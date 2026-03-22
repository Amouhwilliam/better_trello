from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from domain.models.task import Task


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, examples=["Implement login page"])
    deadline: datetime = Field(..., examples=["2026-04-01T12:00:00Z"])
    description: Optional[str] = Field(None, examples=["Use OAuth2 with Google"])


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    deadline: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    deadline: datetime
    completed: bool
    project_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: Task) -> "TaskResponse":
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            deadline=task.deadline,
            completed=task.completed,
            project_id=task.project_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
