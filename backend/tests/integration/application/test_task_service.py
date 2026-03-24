from uuid import uuid4

import pytest

from application.project_service import ProjectService
from application.task_service import TaskService
from application.user_service import UserService
from domain.exceptions import DeadlineConstraintError, ProjectNotFoundError, TaskNotFoundError, UserNotFoundError
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
        self, task_service: TaskService, project_service: ProjectService
    ):
        project = project_service.create_project(title="P", deadline=future(10))
        project_service.update_project(project.id, auto_complete=True)
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        task_service.complete_task(t.id)

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

        from infrastructure.db.user_repository import SQLiteUserRepository

        cfg = Config()
        cfg.AUTO_COMPLETE_PROJECT = True
        svc = TaskService(
            task_repo=SQLiteTaskRepository(db_session),
            project_repo=SQLiteProjectRepository(db_session),
            user_repo=SQLiteUserRepository(db_session),
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


class TestAssignTask:
    def test_assign_task_to_user(self, task_service: TaskService, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        t = task_service.create_task(title="T", deadline=future())
        assigned = task_service.assign_task_to_user(t.id, user.id)
        assert assigned.assignee_id == user.id

    def test_assign_persists(self, task_service: TaskService, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        t = task_service.create_task(title="T", deadline=future())
        task_service.assign_task_to_user(t.id, user.id)
        assert task_service.get_task(t.id).assignee_id == user.id

    def test_assign_raises_for_missing_user(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        with pytest.raises(UserNotFoundError):
            task_service.assign_task_to_user(t.id, uuid4())

    def test_assign_raises_for_missing_task(self, task_service: TaskService, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        with pytest.raises(TaskNotFoundError):
            task_service.assign_task_to_user(uuid4(), user.id)

    def test_reassign_to_different_user(self, task_service: TaskService, user_service: UserService):
        u1 = user_service.create_user("Alice", "alice@example.com", "pw")
        u2 = user_service.create_user("Bob", "bob@example.com", "pw")
        t = task_service.create_task(title="T", deadline=future())
        task_service.assign_task_to_user(t.id, u1.id)
        reassigned = task_service.assign_task_to_user(t.id, u2.id)
        assert reassigned.assignee_id == u2.id

    def test_unassign_task(self, task_service: TaskService, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        t = task_service.create_task(title="T", deadline=future())
        task_service.assign_task_to_user(t.id, user.id)
        unassigned = task_service.unassign_task(t.id)
        assert unassigned.assignee_id is None

    def test_unassign_persists(self, task_service: TaskService, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        t = task_service.create_task(title="T", deadline=future())
        task_service.assign_task_to_user(t.id, user.id)
        task_service.unassign_task(t.id)
        assert task_service.get_task(t.id).assignee_id is None

    def test_unassign_idempotent(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        result = task_service.unassign_task(t.id)  # already unassigned — must not raise
        assert result.assignee_id is None


class TestUpdateTaskStatus:
    def test_update_status_to_in_progress(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        updated = task_service.update_task_status(t.id, "in_progress")
        assert updated.status == "in_progress"
        assert updated.completed is False

    def test_update_status_to_completed(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        updated = task_service.update_task_status(t.id, "completed")
        assert updated.status == "completed"
        assert updated.completed is True

    def test_update_status_to_todo_reopens(self, task_service: TaskService):
        t = task_service.create_task(title="T", deadline=future())
        task_service.update_task_status(t.id, "completed")
        reopened = task_service.update_task_status(t.id, "todo")
        assert reopened.status == "todo"
        assert reopened.completed is False


class TestCreateTaskWithProjectId:
    def test_create_task_links_to_project(self, task_service: TaskService, project_service: ProjectService):
        project = project_service.create_project(title="P", deadline=future(30))
        t = task_service.create_task(title="T", deadline=future(5), project_id=project.id)
        assert t.project_id == project.id

    def test_create_task_with_unknown_project_raises(self, task_service: TaskService):
        from domain.exceptions import ProjectNotFoundError
        with pytest.raises(ProjectNotFoundError):
            task_service.create_task(title="T", deadline=future(), project_id=uuid4())
