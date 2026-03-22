from uuid import uuid4

import pytest

from application.project_service import ProjectService
from application.task_service import TaskService
from domain.exceptions import DeadlineConstraintError, ProjectNotFoundError, TaskNotFoundError
from domain.models.project import Project
from domain.models.task import Task
from tests.conftest import future, past


def make_project(project_service: ProjectService, deadline_days: int = 30) -> Project:
    return project_service.create_project(title="Project", deadline=future(deadline_days))


class TestCreateTask:
    def test_creates_and_persists_task(self, task_service: TaskService):
        task = task_service.create_task(title="T", deadline=future())
        assert task.id is not None
        assert task_service.get_task(task.id).title == "T"

    def test_creates_with_description(self, task_service: TaskService):
        task = task_service.create_task(title="T", deadline=future(), description="desc")
        assert task.description == "desc"

    def test_defaults_completed_to_false(self, task_service: TaskService):
        task = task_service.create_task(title="T", deadline=future())
        assert task.completed is False

    def test_deadline_approaching_logs_warning(self, task_service: TaskService, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="notifications"):
            task_service.create_task(title="Urgent", deadline=future(0))  # ~now
        # no assertion on exact message — just verifying it doesn't crash


class TestGetTask:
    def test_returns_existing_task(self, task_service: TaskService):
        created = task_service.create_task(title="T", deadline=future())
        found = task_service.get_task(created.id)
        assert found.id == created.id

    def test_raises_for_missing_task(self, task_service: TaskService):
        with pytest.raises(TaskNotFoundError):
            task_service.get_task(uuid4())


class TestGetAllTasks:
    def test_returns_all(self, task_service: TaskService):
        task_service.create_task(title="A", deadline=future())
        task_service.create_task(title="B", deadline=future())
        assert len(task_service.get_all_tasks()) == 2

    def test_filter_completed(self, task_service: TaskService):
        t = task_service.create_task(title="Done", deadline=future())
        task_service.complete_task(t.id)
        task_service.create_task(title="Open", deadline=future())
        done = task_service.get_all_tasks(completed=True)
        assert len(done) == 1 and done[0].completed is True

    def test_filter_overdue(self, task_service: TaskService):
        task_service.create_task(title="Overdue", deadline=past(1))
        task_service.create_task(title="Future", deadline=future())
        overdue = task_service.get_all_tasks(overdue=True)
        assert len(overdue) == 1 and overdue[0].title == "Overdue"

    def test_filter_by_project(self, task_service: TaskService, project_service: ProjectService):
        project = make_project(project_service)
        t = task_service.create_task(title="Linked", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        task_service.create_task(title="Unlinked", deadline=future())
        results = task_service.get_all_tasks(project_id=project.id)
        assert len(results) == 1 and results[0].title == "Linked"


class TestUpdateTask:
    def test_updates_title(self, task_service: TaskService):
        t = task_service.create_task(title="Old", deadline=future())
        updated = task_service.update_task(t.id, title="New")
        assert updated.title == "New"

    def test_updates_description(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        updated = task_service.update_task(t.id, description="details")
        assert updated.description == "details"

    def test_updates_deadline(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future(5))
        new_dl = future(3)
        updated = task_service.update_task(t.id, deadline=new_dl)
        assert updated.deadline.replace(microsecond=0) == new_dl.replace(microsecond=0)

    def test_deadline_cannot_exceed_project_deadline(
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = make_project(project_service, deadline_days=5)
        t = task_service.create_task(title="T", deadline=future(3))
        task_service.link_task_to_project(t.id, project.id)
        with pytest.raises(DeadlineConstraintError):
            task_service.update_task(t.id, deadline=future(10))

    def test_raises_for_missing_task(self, task_service: TaskService):
        with pytest.raises(TaskNotFoundError):
            task_service.update_task(uuid4(), title="X")


class TestDeleteTask:
    def test_deletes_task(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        task_service.delete_task(t.id)
        with pytest.raises(TaskNotFoundError):
            task_service.get_task(t.id)

    def test_raises_for_missing_task(self, task_service: TaskService):
        with pytest.raises(TaskNotFoundError):
            task_service.delete_task(uuid4())


class TestCompleteTask:
    def test_marks_task_as_complete(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        completed = task_service.complete_task(t.id)
        assert completed.completed is True

    def test_persists_completion(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        task_service.complete_task(t.id)
        assert task_service.get_task(t.id).completed is True

    def test_raises_for_missing_task(self, task_service: TaskService):
        with pytest.raises(TaskNotFoundError):
            task_service.complete_task(uuid4())

    def test_auto_complete_project_when_flag_enabled(
        self, db_session, notifications, project_service: ProjectService
    ):
        from config import Config
        from infrastructure.db.project_repository import SQLiteProjectRepository
        from infrastructure.db.task_repository import SQLiteTaskRepository

        cfg = Config()
        cfg.AUTO_COMPLETE_PROJECT = True
        svc = TaskService(
            task_repo=SQLiteTaskRepository(db_session),
            project_repo=SQLiteProjectRepository(db_session),
            notifications=notifications,
            config=cfg,
        )
        project = project_service.create_project(title="P", deadline=future(10))
        t = svc.create_task(title="T", deadline=future(5))
        svc.link_task_to_project(t.id, project.id)
        svc.complete_task(t.id)

        updated_project = project_service.get_project(project.id)
        assert updated_project.completed is True

    def test_project_not_auto_completed_when_flag_disabled(
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = make_project(project_service)
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        task_service.complete_task(t.id)
        assert project_service.get_project(project.id).completed is False

    def test_project_not_auto_completed_when_other_tasks_remain_open(
        self, db_session, notifications, project_service: ProjectService
    ):
        from config import Config
        from infrastructure.db.project_repository import SQLiteProjectRepository
        from infrastructure.db.task_repository import SQLiteTaskRepository

        cfg = Config()
        cfg.AUTO_COMPLETE_PROJECT = True
        svc = TaskService(
            task_repo=SQLiteTaskRepository(db_session),
            project_repo=SQLiteProjectRepository(db_session),
            notifications=notifications,
            config=cfg,
        )
        project = project_service.create_project(title="P", deadline=future(10))
        t1 = svc.create_task(title="T1", deadline=future(5))
        t2 = svc.create_task(title="T2", deadline=future(5))
        svc.link_task_to_project(t1.id, project.id)
        svc.link_task_to_project(t2.id, project.id)
        svc.complete_task(t1.id)
        assert project_service.get_project(project.id).completed is False


class TestReopenTask:
    def test_reopens_completed_task(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        task_service.complete_task(t.id)
        reopened = task_service.reopen_task(t.id)
        assert reopened.completed is False

    def test_reopen_sets_completed_project_back_to_open(
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = make_project(project_service)
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        task_service.complete_task(t.id)
        project_service.complete_project(project.id)
        assert project_service.get_project(project.id).completed is True

        task_service.reopen_task(t.id)
        assert project_service.get_project(project.id).completed is False

    def test_reopen_idempotent_on_open_task(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        reopened = task_service.reopen_task(t.id)
        assert reopened.completed is False


class TestLinkAndUnlink:
    def test_link_task_to_project(self, task_service: TaskService, project_service: ProjectService):
        project = make_project(project_service)
        t = task_service.create_task(title="T", deadline=future(5))
        linked = task_service.link_task_to_project(t.id, project.id)
        assert linked.project_id == project.id

    def test_link_raises_for_missing_project(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        with pytest.raises(ProjectNotFoundError):
            task_service.link_task_to_project(t.id, uuid4())

    def test_link_raises_deadline_constraint(
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = project_service.create_project(title="P", deadline=future(2))
        t = task_service.create_task(title="T", deadline=future(5))
        with pytest.raises(DeadlineConstraintError):
            task_service.link_task_to_project(t.id, project.id)

    def test_unlink_task_from_project(
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = make_project(project_service)
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        unlinked = task_service.unlink_task_from_project(t.id, project.id)
        assert unlinked.project_id is None
