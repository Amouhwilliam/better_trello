from datetime import timedelta, timezone
from uuid import uuid4

import pytest

from domain.events import TaskCompleted, TaskReopened
from domain.exceptions import DeadlineConstraintError
from domain.models.task import Task
from tests.conftest import future, past, utc_now


class TestTaskCreation:
    def test_defaults(self):
        task = Task(title="My Task", deadline=future())
        assert task.title == "My Task"
        assert task.description is None
        assert task.completed is False
        assert task.project_id is None
        assert task.id is not None
        assert task.created_at.tzinfo == timezone.utc
        assert task.updated_at.tzinfo == timezone.utc

    def test_unique_ids(self):
        t1 = Task(title="A", deadline=future())
        t2 = Task(title="B", deadline=future())
        assert t1.id != t2.id

    def test_pending_events_start_empty(self):
        task = Task(title="T", deadline=future())
        assert task.pull_events() == []


class TestTaskUpdate:
    def test_update_title(self, task: Task):
        task.update(title="New Title")
        assert task.title == "New Title"

    def test_update_description(self, task: Task):
        task.update(description="Some details")
        assert task.description == "Some details"

    def test_update_deadline_valid(self, task: Task):
        new_deadline = future(5)
        project_deadline = future(10)
        task.update(deadline=new_deadline, project_deadline=project_deadline)
        assert task.deadline == new_deadline

    def test_update_deadline_at_project_deadline_boundary(self, task: Task):
        boundary = future(10)
        task.update(deadline=boundary, project_deadline=boundary)
        assert task.deadline == boundary

    def test_update_deadline_exceeds_project_raises(self, task: Task):
        project_deadline = future(3)
        with pytest.raises(DeadlineConstraintError):
            task.update(deadline=future(5), project_deadline=project_deadline)

    def test_update_without_project_deadline_allows_any_deadline(self, task: Task):
        far_future = future(365)
        task.update(deadline=far_future)
        assert task.deadline == far_future

    def test_update_sets_updated_at(self, task: Task):
        before = task.updated_at
        task.update(title="Changed")
        assert task.updated_at >= before


class TestTaskProjectAssociation:
    def test_assign_to_project(self, task: Task):
        project_id = uuid4()
        project_deadline = future(30)
        task.assign_to_project(project_id, project_deadline)
        assert task.project_id == project_id

    def test_assign_to_project_deadline_violation_raises(self, task: Task):
        project_deadline = future(1)
        task_deadline = future(5)
        task.deadline = task_deadline
        with pytest.raises(DeadlineConstraintError):
            task.assign_to_project(uuid4(), project_deadline)

    def test_unlink_from_project(self, task_in_project: Task):
        assert task_in_project.project_id is not None
        task_in_project.unlink_from_project()
        assert task_in_project.project_id is None

    def test_unlink_sets_updated_at(self, task_in_project: Task):
        before = task_in_project.updated_at
        task_in_project.unlink_from_project()
        assert task_in_project.updated_at >= before


class TestTaskCompletion:
    def test_mark_complete_sets_flag(self, task: Task):
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_emits_event(self, task: Task):
        task.mark_complete()
        events = task.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskCompleted)
        assert events[0].task_id == task.id

    def test_mark_complete_idempotent_no_duplicate_events(self, task: Task):
        task.mark_complete()
        task.pull_events()
        task.mark_complete()
        assert task.pull_events() == []

    def test_mark_complete_sets_updated_at(self, task: Task):
        before = task.updated_at
        task.mark_complete()
        assert task.updated_at >= before


class TestTaskReopen:
    def test_reopen_clears_flag(self, task: Task):
        task.mark_complete()
        task.pull_events()
        task.reopen()
        assert task.completed is False

    def test_reopen_emits_event(self, task_in_project: Task):
        task_in_project.mark_complete()
        task_in_project.pull_events()
        task_in_project.reopen()
        events = task_in_project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], TaskReopened)
        assert events[0].task_id == task_in_project.id
        assert events[0].project_id == task_in_project.project_id

    def test_reopen_idempotent_on_open_task(self, task: Task):
        task.reopen()
        assert task.pull_events() == []

    def test_reopen_sets_updated_at(self, task: Task):
        task.mark_complete()
        task.pull_events()
        before = task.updated_at
        task.reopen()
        assert task.updated_at >= before


class TestTaskAdjustDeadline:
    def test_adjust_deadline_force_sets(self, task: Task):
        new_deadline = future(1)
        task.adjust_deadline(new_deadline)
        assert task.deadline == new_deadline

    def test_adjust_deadline_sets_updated_at(self, task: Task):
        before = task.updated_at
        task.adjust_deadline(future(2))
        assert task.updated_at >= before

    def test_adjust_deadline_does_not_validate_against_project(self, task_in_project: Task):
        # adjust_deadline is an internal force-set, no exception expected
        new_deadline = future(100)
        task_in_project.adjust_deadline(new_deadline)
        assert task_in_project.deadline == new_deadline


class TestTaskOverdue:
    def test_overdue_past_deadline_incomplete(self, task: Task):
        task.deadline = past(1)
        assert task.is_overdue() is True

    def test_not_overdue_future_deadline(self, task: Task):
        task.deadline = future(1)
        assert task.is_overdue() is False

    def test_not_overdue_when_completed(self, task: Task):
        task.deadline = past(1)
        task.mark_complete()
        assert task.is_overdue() is False


class TestTaskPullEvents:
    def test_pull_events_clears_queue(self, task: Task):
        task.mark_complete()
        task.pull_events()
        assert task.pull_events() == []

    def test_pull_events_accumulates_multiple(self, task: Task):
        task.mark_complete()
        task.pull_events()
        task.reopen()
        task.mark_complete()
        events = task.pull_events()
        assert len(events) == 2
        assert isinstance(events[0], TaskReopened)
        assert isinstance(events[1], TaskCompleted)
