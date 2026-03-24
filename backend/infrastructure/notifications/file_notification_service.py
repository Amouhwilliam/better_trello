"""
File-based notification adapter — writes every domain event to a rotating log file.
This is an infrastructure adapter: it implements NotificationPort using the standard
library's RotatingFileHandler so log files never grow unbounded.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler

from domain.events import (
    DomainEvent,
    ProjectCompleted,
    ProjectDeadlineUpdated,
    TaskCompleted,
    TaskReopened,
)
from domain.models.task import Task
from domain.ports.notification_port import NotificationPort

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 3              # keep up to 3 rotated files


def _build_file_logger(log_path: str) -> logging.Logger:
    # Use an absolute, normalised path as part of the logger name so that
    # each distinct file gets its own logger (important for test isolation).
    abs_path = os.path.abspath(log_path)
    logger_name = f"notifications.file.{abs_path}"
    logger = logging.getLogger(logger_name)
    if logger.handlers:          # already initialised (e.g. on hot-reload)
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False     # don't bubble up to the root logger

    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(handler)
    return logger


class FileNotificationService(NotificationPort):
    """Writes notification events to a persistent log file."""

    def __init__(self, log_path: str) -> None:
        self._logger = _build_file_logger(log_path)

    def dispatch(self, event: DomainEvent) -> None:
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
        if task.completed:
            return
        time_left = task.deadline - datetime.now(timezone.utc)
        if timedelta(0) < time_left <= timedelta(hours=24):
            hours_left = int(time_left.total_seconds() // 3600)
            minutes_left = int((time_left.total_seconds() % 3600) // 60)
            self._logger.warning(
                "Deadline approaching — task '%s' (id=%s) is due in %dh %02dm (deadline: %s).",
                task.title,
                task.id,
                hours_left,
                minutes_left,
                task.deadline.strftime("%Y-%m-%d %H:%M UTC"),
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_task_completed(self, event: TaskCompleted) -> None:
        self._logger.info(
            "Task completed — '%s' (id=%s).", event.task_title, event.task_id
        )

    def _on_task_reopened(self, event: TaskReopened) -> None:
        if event.project_id:
            self._logger.info(
                "Task reopened — '%s' (id=%s) in project (id=%s).",
                event.task_title,
                event.task_id,
                event.project_id,
            )
        else:
            self._logger.info(
                "Task reopened — '%s' (id=%s).", event.task_title, event.task_id
            )

    def _on_project_deadline_updated(self, event: ProjectDeadlineUpdated) -> None:
        self._logger.warning(
            "Project deadline moved earlier — '%s' (id=%s): %s → %s. "
            "%d task(s) had their deadline clamped.",
            event.project_title,
            event.project_id,
            event.old_deadline.strftime("%Y-%m-%d"),
            event.new_deadline.strftime("%Y-%m-%d"),
            len(event.affected_task_ids),
        )

    def _on_project_completed(self, event: ProjectCompleted) -> None:
        self._logger.info(
            "Project completed — '%s' (id=%s).", event.project_title, event.project_id
        )
