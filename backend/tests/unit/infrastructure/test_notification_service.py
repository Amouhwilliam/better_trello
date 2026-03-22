import logging
from datetime import timedelta, timezone
from uuid import uuid4

import pytest

from domain.events import (
    ProjectCompleted,
    ProjectDeadlineUpdated,
    TaskCompleted,
    TaskReopened,
)
from domain.models.task import Task
from infrastructure.notifications.notification_service import NotificationService
from tests.conftest import future, past, utc_now


@pytest.fixture
def svc() -> NotificationService:
    return NotificationService()


class TestDispatchTaskCompleted:
    def test_logs_info(self, svc: NotificationService, caplog):
        task_id = uuid4()
        with caplog.at_level(logging.INFO, logger="notifications"):
            svc.dispatch(TaskCompleted(task_id=task_id))
        assert str(task_id) in caplog.text
        assert caplog.records[0].levelname == "INFO"


class TestDispatchTaskReopened:
    def test_logs_info(self, svc: NotificationService, caplog):
        task_id = uuid4()
        project_id = uuid4()
        with caplog.at_level(logging.INFO, logger="notifications"):
            svc.dispatch(TaskReopened(task_id=task_id, project_id=project_id))
        assert str(task_id) in caplog.text
        assert caplog.records[0].levelname == "INFO"

    def test_logs_info_without_project(self, svc: NotificationService, caplog):
        with caplog.at_level(logging.INFO, logger="notifications"):
            svc.dispatch(TaskReopened(task_id=uuid4(), project_id=None))
        assert caplog.records[0].levelname == "INFO"


class TestDispatchProjectDeadlineUpdated:
    def test_logs_warning(self, svc: NotificationService, caplog):
        project_id = uuid4()
        affected_id = uuid4()
        event = ProjectDeadlineUpdated(
            project_id=project_id,
            old_deadline=future(10),
            new_deadline=future(5),
            affected_task_ids=[affected_id],
        )
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.dispatch(event)
        assert str(project_id) in caplog.text
        assert str(affected_id) in caplog.text
        assert caplog.records[0].levelname == "WARNING"

    def test_logs_warning_with_multiple_affected_tasks(self, svc: NotificationService, caplog):
        ids = [uuid4(), uuid4(), uuid4()]
        event = ProjectDeadlineUpdated(
            project_id=uuid4(),
            old_deadline=future(20),
            new_deadline=future(5),
            affected_task_ids=ids,
        )
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.dispatch(event)
        for tid in ids:
            assert str(tid) in caplog.text


class TestDispatchProjectCompleted:
    def test_logs_info(self, svc: NotificationService, caplog):
        project_id = uuid4()
        with caplog.at_level(logging.INFO, logger="notifications"):
            svc.dispatch(ProjectCompleted(project_id=project_id))
        assert str(project_id) in caplog.text
        assert caplog.records[0].levelname == "INFO"


class TestDispatchAll:
    def test_dispatches_each_event(self, svc: NotificationService, caplog):
        events = [
            TaskCompleted(task_id=uuid4()),
            ProjectCompleted(project_id=uuid4()),
        ]
        with caplog.at_level(logging.INFO, logger="notifications"):
            svc.dispatch_all(events)
        assert len(caplog.records) == 2

    def test_empty_list_does_nothing(self, svc: NotificationService, caplog):
        with caplog.at_level(logging.DEBUG, logger="notifications"):
            svc.dispatch_all([])
        assert caplog.records == []


class TestCheckDeadlineApproaching:
    def test_warns_when_deadline_within_24h(self, svc: NotificationService, caplog):
        task = Task(title="Urgent", deadline=utc_now() + timedelta(hours=12))
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.check_deadline_approaching(task)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Urgent" in caplog.text

    def test_warns_exactly_at_24h_boundary(self, svc: NotificationService, caplog):
        task = Task(title="T", deadline=utc_now() + timedelta(hours=23, minutes=59))
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.check_deadline_approaching(task)
        assert len(caplog.records) == 1

    def test_no_warn_when_deadline_beyond_24h(self, svc: NotificationService, caplog):
        task = Task(title="T", deadline=future(7))
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.check_deadline_approaching(task)
        assert caplog.records == []

    def test_no_warn_when_task_completed(self, svc: NotificationService, caplog):
        task = Task(title="T", deadline=utc_now() + timedelta(hours=1))
        task.mark_complete()
        task.pull_events()
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.check_deadline_approaching(task)
        assert caplog.records == []

    def test_no_warn_when_overdue(self, svc: NotificationService, caplog):
        task = Task(title="T", deadline=past(1))
        with caplog.at_level(logging.WARNING, logger="notifications"):
            svc.check_deadline_approaching(task)
        assert caplog.records == []
