"""
In-memory notification service — reacts to domain events by logging.
This is an infrastructure adapter: it knows about domain events but the
domain itself has no dependency on it.
"""

import logging
from datetime import datetime, timedelta, timezone

from domain.events import (
    DomainEvent,
    ProjectCompleted,
    ProjectDeadlineUpdated,
    TaskCompleted,
    TaskReopened,
)
from domain.models.task import Task

logger = logging.getLogger("notifications")


class NotificationService:
    def dispatch(self, event: DomainEvent) -> None:
        """Route a domain event to the appropriate handler."""
        if isinstance(event, TaskCompleted):
            self._on_task_completed(event)
        elif isinstance(event, TaskReopened):
            self._on_task_reopened(event)
        elif isinstance(event, ProjectDeadlineUpdated):
            self._on_project_deadline_updated(event)
        elif isinstance(event, ProjectCompleted):
            self._on_project_completed(event)

    def dispatch_all(self, events: list) -> None:
        for event in events:
            self.dispatch(event)

    def check_deadline_approaching(self, task: Task) -> None:
        """Warn if the task deadline is within 24 hours and not yet completed."""
        if task.completed:
            return
        time_left = task.deadline - datetime.now(timezone.utc)
        if timedelta(0) < time_left <= timedelta(hours=24):
            logger.warning(
                "Task '%s' (id=%s) deadline is approaching in less than 24 hours (%s).",
                task.title,
                task.id,
                task.deadline.isoformat(),
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_task_completed(self, event: TaskCompleted) -> None:
        logger.info("Task completed (id=%s).", event.task_id)

    def _on_task_reopened(self, event: TaskReopened) -> None:
        logger.info(
            "Task reopened (id=%s, project_id=%s).",
            event.task_id,
            event.project_id,
        )

    def _on_project_deadline_updated(self, event: ProjectDeadlineUpdated) -> None:
        logger.warning(
            "Project deadline moved earlier (project_id=%s). "
            "Affected task ids: %s. New deadline: %s.",
            event.project_id,
            [str(tid) for tid in event.affected_task_ids],
            event.new_deadline.isoformat(),
        )

    def _on_project_completed(self, event: ProjectCompleted) -> None:
        logger.info("Project completed (id=%s).", event.project_id)
