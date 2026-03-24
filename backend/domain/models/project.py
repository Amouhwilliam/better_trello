from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from domain.events import ProjectCompleted, ProjectDeadlineUpdated
from domain.exceptions import ProjectCompletionError

if TYPE_CHECKING:
    from domain.models.task import Task


@dataclass
class Project:
    title: str
    deadline: datetime
    id: UUID = field(default_factory=uuid4)
    owner_id: Optional[UUID] = None
    completed: bool = False
    auto_complete: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _pending_events: list = field(default_factory=list, init=False, repr=False, compare=False)

    def update(self, title: Optional[str] = None, deadline: Optional[datetime] = None, tasks: Optional[List["Task"]] = None) -> None:
        if deadline is not None:
            self._update_deadline(deadline, tasks or [])
        if title is not None:
            self.title = title
        self.updated_at = datetime.now(timezone.utc)

    def _update_deadline(self, new_deadline: datetime, tasks: List["Task"]) -> None:
        old_deadline = self.deadline
        self.deadline = new_deadline

        if new_deadline < old_deadline:
            affected_task_ids = [t.id for t in tasks if t.deadline > new_deadline]
            if affected_task_ids:
                self._pending_events.append(
                    ProjectDeadlineUpdated(
                        project_id=self.id,
                        project_title=self.title,
                        old_deadline=old_deadline,
                        new_deadline=new_deadline,
                        affected_task_ids=affected_task_ids,
                    )
                )

    def mark_complete(self, tasks: List["Task"]) -> None:
        if any(not t.completed for t in tasks):
            raise ProjectCompletionError(
                "Cannot complete project: all tasks must be completed first"
            )
        if not self.completed:
            self.completed = True
            self.updated_at = datetime.now(timezone.utc)
            self._pending_events.append(ProjectCompleted(project_id=self.id, project_title=self.title))

    def reopen(self) -> None:
        if self.completed:
            self.completed = False
            self.updated_at = datetime.now(timezone.utc)

    def try_auto_complete(self, tasks: List["Task"]) -> None:
        """Mark project complete if all tasks are done and the per-project flag is on."""
        if self.auto_complete and tasks and all(t.completed for t in tasks):
            self.mark_complete(tasks)

    def pull_events(self) -> list:
        events = list(self._pending_events)
        self._pending_events.clear()
        return events
