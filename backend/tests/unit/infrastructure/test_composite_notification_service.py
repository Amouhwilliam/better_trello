"""
Unit tests for CompositeNotificationService.
Uses mock adapters to verify fan-out behaviour without any I/O.
"""
from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from domain.events import ProjectCompleted, TaskCompleted, TaskReopened
from domain.models.task import Task
from infrastructure.notifications.composite_notification_service import CompositeNotificationService
from tests.conftest import future, utc_now


@pytest.fixture
def adapter_a():
    return MagicMock()


@pytest.fixture
def adapter_b():
    return MagicMock()


@pytest.fixture
def svc(adapter_a, adapter_b):
    return CompositeNotificationService(adapter_a, adapter_b)


class TestCompositeDispatch:
    def test_dispatch_calls_all_adapters(self, svc, adapter_a, adapter_b):
        event = TaskCompleted(task_id=uuid4(), task_title="T")
        svc.dispatch(event)
        adapter_a.dispatch.assert_called_once_with(event)
        adapter_b.dispatch.assert_called_once_with(event)

    def test_dispatch_all_calls_each_adapter_for_each_event(self, svc, adapter_a, adapter_b):
        events = [
            TaskCompleted(task_id=uuid4(), task_title="T1"),
            ProjectCompleted(project_id=uuid4(), project_title="P1"),
        ]
        svc.dispatch_all(events)
        assert adapter_a.dispatch.call_count == 2
        assert adapter_b.dispatch.call_count == 2

    def test_dispatch_all_empty_list_calls_nothing(self, svc, adapter_a, adapter_b):
        svc.dispatch_all([])
        adapter_a.dispatch.assert_not_called()
        adapter_b.dispatch.assert_not_called()

    def test_check_deadline_approaching_calls_all_adapters(self, svc, adapter_a, adapter_b):
        task = Task(title="T", deadline=utc_now() + timedelta(hours=12))
        svc.check_deadline_approaching(task)
        adapter_a.check_deadline_approaching.assert_called_once_with(task)
        adapter_b.check_deadline_approaching.assert_called_once_with(task)

    def test_works_with_single_adapter(self, adapter_a):
        svc = CompositeNotificationService(adapter_a)
        event = TaskCompleted(task_id=uuid4(), task_title="Solo")
        svc.dispatch(event)
        adapter_a.dispatch.assert_called_once_with(event)

    def test_works_with_no_adapters(self):
        svc = CompositeNotificationService()
        # Should not raise
        svc.dispatch(TaskCompleted(task_id=uuid4(), task_title="No-op"))
        svc.dispatch_all([])
        svc.check_deadline_approaching(Task(title="T", deadline=future(1)))
