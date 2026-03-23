from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from domain.events import TaskCompleted, TaskReopened
from domain.exceptions import DeadlineConstraintError


@dataclass
class Task:
    title: str
    deadline: datetime
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    completed: bool = False
    project_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _pending_events: list = field(default_factory=list, init=False, repr=False, compare=False)

    def _validate_deadline(self, deadline: datetime, project_deadline: Optional[datetime]) -> None:
        if project_deadline is not None and deadline > project_deadline:
            raise DeadlineConstraintError(
                f"Task deadline ({deadline.isoformat()}) cannot exceed "
                f"project deadline ({project_deadline.isoformat()})"
            )

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
        project_deadline: Optional[datetime] = None,
    ) -> None:
        if deadline is not None:
            self._validate_deadline(deadline, project_deadline)
            self.deadline = deadline
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        self.updated_at = datetime.now(timezone.utc)

    def assign_to_project(self, project_id: UUID, project_deadline: datetime) -> None:
        self._validate_deadline(self.deadline, project_deadline)
        self.project_id = project_id
        self.updated_at = datetime.now(timezone.utc)

    def unlink_from_project(self) -> None:
        self.project_id = None
        self.updated_at = datetime.now(timezone.utc)

    def assign_to_user(self, user_id: UUID) -> None:
        self.assignee_id = user_id
        self.updated_at = datetime.now(timezone.utc)

    def unassign(self) -> None:
        self.assignee_id = None
        self.updated_at = datetime.now(timezone.utc)

    def mark_complete(self) -> None:
        if not self.completed:
            self.completed = True
            self.updated_at = datetime.now(timezone.utc)
            self._pending_events.append(TaskCompleted(task_id=self.id, task_title=self.title))

    def reopen(self) -> None:
        if self.completed:
            self.completed = False
            self.updated_at = datetime.now(timezone.utc)
            self._pending_events.append(TaskReopened(task_id=self.id, task_title=self.title, project_id=self.project_id))

    def adjust_deadline(self, new_deadline: datetime) -> None:
        """Force-adjust deadline (used when project deadline is moved earlier)."""
        self.deadline = new_deadline
        self.updated_at = datetime.now(timezone.utc)

    def is_overdue(self) -> bool:
        return not self.completed and datetime.now(timezone.utc) > self.deadline

    def pull_events(self) -> list:
        events = list(self._pending_events)
        self._pending_events.clear()
        return events
