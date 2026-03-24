from datetime import timedelta, timezone
from uuid import uuid4

import pytest

from domain.events import ProjectCompleted, ProjectDeadlineUpdated
from domain.exceptions import ProjectCompletionError
from domain.models.project import Project
from domain.models.task import Task
from tests.conftest import future, past, utc_now


def make_completed_task(project: Project) -> Task:
    t = Task(title="Done Task", deadline=future(5))
    t.assign_to_project(project.id, project.deadline)
    t.mark_complete()
    t.pull_events()
    return t


def make_open_task(project: Project) -> Task:
    t = Task(title="Open Task", deadline=future(5))
    t.assign_to_project(project.id, project.deadline)
    return t


class TestProjectCreation:
    def test_defaults(self):
        p = Project(title="My Project", deadline=future(30))
        assert p.title == "My Project"
        assert p.completed is False
        assert p.id is not None
        assert p.created_at.tzinfo == timezone.utc
        assert p.updated_at.tzinfo == timezone.utc

    def test_unique_ids(self):
        p1 = Project(title="A", deadline=future())
        p2 = Project(title="B", deadline=future())
        assert p1.id != p2.id

    def test_pending_events_start_empty(self):
        p = Project(title="P", deadline=future())
        assert p.pull_events() == []


class TestProjectUpdate:
    def test_update_title(self, project: Project):
        project.update(title="Renamed")
        assert project.title == "Renamed"

    def test_update_title_sets_updated_at(self, project: Project):
        before = project.updated_at
        project.update(title="X")
        assert project.updated_at >= before

    def test_update_deadline_later_no_event(self, project: Project):
        t = make_open_task(project)
        project.update(deadline=future(60), tasks=[t])
        assert project.pull_events() == []

    def test_update_deadline_earlier_with_affected_tasks_emits_event(self, project: Project):
        t = Task(title="Late Task", deadline=future(20))
        t.assign_to_project(project.id, project.deadline)
        new_deadline = future(10)
        project.update(deadline=new_deadline, tasks=[t])
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectDeadlineUpdated)
        assert events[0].project_id == project.id
        assert events[0].new_deadline == new_deadline
        assert t.id in events[0].affected_task_ids

    def test_update_deadline_earlier_no_affected_tasks_no_event(self, project: Project):
        t = Task(title="Early Task", deadline=future(2))
        t.assign_to_project(project.id, project.deadline)
        project.update(deadline=future(5), tasks=[t])
        assert project.pull_events() == []

    def test_update_deadline_earlier_empty_task_list_no_event(self, project: Project):
        project.update(deadline=future(1), tasks=[])
        assert project.pull_events() == []

    def test_update_sets_new_deadline(self, project: Project):
        new_deadline = future(15)
        project.update(deadline=new_deadline)
        assert project.deadline == new_deadline


class TestProjectCompletion:
    def test_mark_complete_all_tasks_done(self, project: Project):
        tasks = [make_completed_task(project), make_completed_task(project)]
        project.mark_complete(tasks)
        assert project.completed is True

    def test_mark_complete_emits_event(self, project: Project):
        tasks = [make_completed_task(project)]
        project.mark_complete(tasks)
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectCompleted)
        assert events[0].project_id == project.id

    def test_mark_complete_with_open_task_raises(self, project: Project):
        tasks = [make_completed_task(project), make_open_task(project)]
        with pytest.raises(ProjectCompletionError):
            project.mark_complete(tasks)

    def test_mark_complete_with_no_tasks_succeeds(self, project: Project):
        project.mark_complete([])
        assert project.completed is True

    def test_mark_complete_idempotent_no_duplicate_events(self, project: Project):
        tasks = [make_completed_task(project)]
        project.mark_complete(tasks)
        project.pull_events()
        project.mark_complete(tasks)
        assert project.pull_events() == []

    def test_mark_complete_sets_updated_at(self, project: Project):
        before = project.updated_at
        project.mark_complete([])
        assert project.updated_at >= before


class TestProjectReopen:
    def test_reopen_clears_flag(self, project: Project):
        project.mark_complete([])
        project.pull_events()
        project.reopen()
        assert project.completed is False

    def test_reopen_sets_updated_at(self, project: Project):
        project.mark_complete([])
        project.pull_events()
        before = project.updated_at
        project.reopen()
        assert project.updated_at >= before

    def test_reopen_idempotent_on_open_project(self, project: Project):
        project.reopen()
        assert project.completed is False


class TestProjectAutoComplete:
    def test_auto_complete_enabled_all_tasks_done(self, project: Project):
        project.auto_complete = True
        tasks = [make_completed_task(project)]
        project.try_auto_complete(tasks)
        assert project.completed is True

    def test_auto_complete_enabled_emits_event(self, project: Project):
        project.auto_complete = True
        tasks = [make_completed_task(project)]
        project.try_auto_complete(tasks)
        events = project.pull_events()
        assert any(isinstance(e, ProjectCompleted) for e in events)

    def test_auto_complete_disabled_does_nothing(self, project: Project):
        project.auto_complete = False
        tasks = [make_completed_task(project)]
        project.try_auto_complete(tasks)
        assert project.completed is False
        assert project.pull_events() == []

    def test_auto_complete_with_open_task_does_not_complete(self, project: Project):
        project.auto_complete = True
        tasks = [make_completed_task(project), make_open_task(project)]
        project.try_auto_complete(tasks)
        assert project.completed is False

    def test_auto_complete_empty_task_list_does_nothing(self, project: Project):
        project.auto_complete = True
        project.try_auto_complete([])
        assert project.completed is False


class TestProjectPullEvents:
    def test_pull_events_clears_queue(self, project: Project):
        project.mark_complete([])
        project.pull_events()
        assert project.pull_events() == []

    def test_pull_events_deadline_event(self, project: Project):
        t = Task(title="Late", deadline=future(20))
        t.assign_to_project(project.id, project.deadline)
        project.update(deadline=future(10), tasks=[t])
        events = project.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ProjectDeadlineUpdated)
        assert project.pull_events() == []
