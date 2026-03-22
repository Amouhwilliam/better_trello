from uuid import uuid4

import pytest

from application.project_service import ProjectService
from application.task_service import TaskService
from domain.exceptions import ProjectCompletionError, ProjectNotFoundError
from domain.models.project import Project
from tests.conftest import future, past


class TestCreateProject:
    def test_creates_and_persists(self, project_service: ProjectService):
        project = project_service.create_project(title="P", deadline=future(30))
        assert project.id is not None
        assert project_service.get_project(project.id).title == "P"

    def test_defaults_completed_to_false(self, project_service: ProjectService):
        project = project_service.create_project(title="P", deadline=future())
        assert project.completed is False


class TestGetProject:
    def test_returns_existing_project(self, project_service: ProjectService):
        created = project_service.create_project(title="P", deadline=future())
        found = project_service.get_project(created.id)
        assert found.id == created.id

    def test_raises_for_missing_project(self, project_service: ProjectService):
        with pytest.raises(ProjectNotFoundError):
            project_service.get_project(uuid4())


class TestGetAllProjects:
    def test_returns_all(self, project_service: ProjectService):
        project_service.create_project(title="A", deadline=future())
        project_service.create_project(title="B", deadline=future())
        assert len(project_service.get_all_projects()) == 2

    def test_empty_returns_empty_list(self, project_service: ProjectService):
        assert project_service.get_all_projects() == []


class TestUpdateProject:
    def test_updates_title(self, project_service: ProjectService):
        p = project_service.create_project(title="Old", deadline=future(30))
        updated = project_service.update_project(p.id, title="New")
        assert updated.title == "New"

    def test_updates_deadline(self, project_service: ProjectService):
        p = project_service.create_project(title="P", deadline=future(30))
        new_dl = future(20)
        updated = project_service.update_project(p.id, deadline=new_dl)
        assert updated.deadline.replace(microsecond=0) == new_dl.replace(microsecond=0)

    def test_raises_for_missing_project(self, project_service: ProjectService):
        with pytest.raises(ProjectNotFoundError):
            project_service.update_project(uuid4(), title="X")

    def test_moving_deadline_earlier_adjusts_affected_task_deadlines(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(30))
        t = task_service.create_task(title="T", deadline=future(20))
        task_service.link_task_to_project(t.id, project.id)

        new_project_deadline = future(10)
        project_service.update_project(project.id, deadline=new_project_deadline)

        updated_task = task_service.get_task(t.id)
        assert updated_task.deadline.replace(microsecond=0) == new_project_deadline.replace(
            microsecond=0
        )

    def test_moving_deadline_later_does_not_touch_tasks(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(30))
        original_deadline = future(10)
        t = task_service.create_task(title="T", deadline=original_deadline)
        task_service.link_task_to_project(t.id, project.id)

        project_service.update_project(project.id, deadline=future(60))

        updated_task = task_service.get_task(t.id)
        assert updated_task.deadline.replace(microsecond=0) == original_deadline.replace(
            microsecond=0
        )

    def test_moving_deadline_earlier_only_adjusts_affected_tasks(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(30))
        late_task = task_service.create_task(title="Late", deadline=future(20))
        early_task = task_service.create_task(title="Early", deadline=future(5))
        task_service.link_task_to_project(late_task.id, project.id)
        task_service.link_task_to_project(early_task.id, project.id)

        project_service.update_project(project.id, deadline=future(10))

        assert task_service.get_task(late_task.id).deadline.replace(
            microsecond=0
        ) == future(10).replace(microsecond=0)
        assert task_service.get_task(early_task.id).deadline.replace(
            microsecond=0
        ) == future(5).replace(microsecond=0)


class TestCompleteProject:
    def test_completes_when_all_tasks_done(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(10))
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)
        task_service.complete_task(t.id)

        completed = project_service.complete_project(project.id)
        assert completed.completed is True

    def test_raises_when_open_tasks_exist(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(10))
        t = task_service.create_task(title="T", deadline=future(5))
        task_service.link_task_to_project(t.id, project.id)

        with pytest.raises(ProjectCompletionError):
            project_service.complete_project(project.id)

    def test_completes_with_no_tasks(self, project_service: ProjectService):
        project = project_service.create_project(title="P", deadline=future())
        completed = project_service.complete_project(project.id)
        assert completed.completed is True

    def test_raises_for_missing_project(self, project_service: ProjectService):
        with pytest.raises(ProjectNotFoundError):
            project_service.complete_project(uuid4())

    def test_persists_completion(self, project_service: ProjectService):
        p = project_service.create_project(title="P", deadline=future())
        project_service.complete_project(p.id)
        assert project_service.get_project(p.id).completed is True


class TestDeleteProject:
    def test_deletes_project(self, project_service: ProjectService):
        p = project_service.create_project(title="P", deadline=future())
        project_service.delete_project(p.id)
        with pytest.raises(ProjectNotFoundError):
            project_service.get_project(p.id)

    def test_raises_for_missing_project(self, project_service: ProjectService):
        with pytest.raises(ProjectNotFoundError):
            project_service.delete_project(uuid4())


class TestGetProjectTasks:
    def test_returns_tasks_for_project(
        self, project_service: ProjectService, task_service: TaskService
    ):
        project = project_service.create_project(title="P", deadline=future(10))
        t1 = task_service.create_task(title="T1", deadline=future(5))
        t2 = task_service.create_task(title="T2", deadline=future(5))
        task_service.link_task_to_project(t1.id, project.id)
        task_service.link_task_to_project(t2.id, project.id)
        task_service.create_task(title="Other", deadline=future())

        tasks = project_service.get_project_tasks(project.id)
        assert len(tasks) == 2

    def test_returns_empty_for_project_with_no_tasks(self, project_service: ProjectService):
        project = project_service.create_project(title="P", deadline=future())
        assert project_service.get_project_tasks(project.id) == []

    def test_raises_for_missing_project(self, project_service: ProjectService):
        with pytest.raises(ProjectNotFoundError):
            project_service.get_project_tasks(uuid4())
