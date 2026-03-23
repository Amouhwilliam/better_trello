from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Union
from uuid import UUID


@dataclass
class TaskCompleted:
    task_id: UUID
    task_title: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskReopened:
    task_id: UUID
    task_title: str
    project_id: Optional[UUID]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ProjectDeadlineUpdated:
    project_id: UUID
    project_title: str
    old_deadline: datetime
    new_deadline: datetime
    affected_task_ids: List[UUID]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ProjectCompleted:
    project_id: UUID
    project_title: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


DomainEvent = Union[TaskCompleted, TaskReopened, ProjectDeadlineUpdated, ProjectCompleted]
