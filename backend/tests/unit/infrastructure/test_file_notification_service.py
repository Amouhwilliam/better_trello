"""
Unit tests for FileNotificationService.
Uses a temp directory so no real /app/data path is required.
"""
import logging
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from domain.events import (
    ProjectCompleted,
    ProjectDeadlineUpdated,
    TaskCompleted,
    TaskReopened,
)
from domain.models.task import Task
from infrastructure.notifications.file_notification_service import FileNotificationService
from tests.conftest import future, past, utc_now


@pytest.fixture
def log_path(tmp_path: Path) -> str:
    return str(tmp_path / "notifications.log")


@pytest.fixture
def svc(log_path: str) -> FileNotificationService:
    return FileNotificationService(log_path)


def _read_log(log_path: str) -> str:
    return Path(log_path).read_text(encoding="utf-8")


class TestFileNotificationServiceTaskCompleted:
    def test_writes_task_completed(self, svc, log_path):
        task_id = uuid4()
        svc.dispatch(TaskCompleted(task_id=task_id, task_title="Deploy app"))
        content = _read_log(log_path)
        assert str(task_id) in content
        assert "Deploy app" in content
        assert "INFO" in content

    def test_task_reopened_with_project(self, svc, log_path):
        task_id, project_id = uuid4(), uuid4()
        svc.dispatch(TaskReopened(task_id=task_id, task_title="Reopen", project_id=project_id))
        content = _read_log(log_path)
        assert str(task_id) in content
        assert str(project_id) in content

    def test_task_reopened_without_project(self, svc, log_path):
        task_id = uuid4()
        svc.dispatch(TaskReopened(task_id=task_id, task_title="No proj", project_id=None))
        content = _read_log(log_path)
        assert "No proj" in content

    def test_project_deadline_updated_writes_warning(self, svc, log_path):
        project_id = uuid4()
        svc.dispatch(ProjectDeadlineUpdated(
            project_id=project_id,
            project_title="Q3",
            old_deadline=future(10),
            new_deadline=future(5),
            affected_task_ids=[uuid4(), uuid4()],
        ))
        content = _read_log(log_path)
        assert str(project_id) in content
        assert "Q3" in content
        assert "WARNING" in content
        assert "2" in content

    def test_project_completed_writes_info(self, svc, log_path):
        project_id = uuid4()
        svc.dispatch(ProjectCompleted(project_id=project_id, project_title="Launch"))
        content = _read_log(log_path)
        assert str(project_id) in content
        assert "Launch" in content

    def test_dispatch_all_writes_multiple_entries(self, svc, log_path):
        events = [
            TaskCompleted(task_id=uuid4(), task_title="T1"),
            ProjectCompleted(project_id=uuid4(), project_title="P1"),
        ]
        svc.dispatch_all(events)
        content = _read_log(log_path)
        assert "T1" in content
        assert "P1" in content

    def test_deadline_approaching_writes_warning(self, svc, log_path):
        task = Task(title="Urgent", deadline=utc_now() + timedelta(hours=6))
        svc.check_deadline_approaching(task)
        content = _read_log(log_path)
        assert "Urgent" in content
        assert "WARNING" in content

    def test_no_warning_when_beyond_24h(self, svc, log_path):
        task = Task(title="Safe", deadline=future(7))
        svc.check_deadline_approaching(task)
        assert not Path(log_path).exists() or _read_log(log_path) == ""

    def test_no_warning_when_completed(self, svc, log_path):
        task = Task(title="Done", deadline=utc_now() + timedelta(hours=1))
        task.mark_complete()
        task.pull_events()
        svc.check_deadline_approaching(task)
        assert not Path(log_path).exists() or _read_log(log_path) == ""

    def test_creates_parent_directory(self, tmp_path):
        nested_path = str(tmp_path / "deep" / "dir" / "notify.log")
        svc = FileNotificationService(nested_path)
        svc.dispatch(TaskCompleted(task_id=uuid4(), task_title="Nested"))
        assert Path(nested_path).exists()
