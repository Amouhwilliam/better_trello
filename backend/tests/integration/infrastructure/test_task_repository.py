from datetime import timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from domain.models.project import Project
from domain.models.task import Task
from infrastructure.db.project_repository import SQLiteProjectRepository
from infrastructure.db.task_repository import SQLiteTaskRepository
from tests.conftest import future, past


def make_repo(db: Session) -> SQLiteTaskRepository:
    return SQLiteTaskRepository(db)


def make_project_repo(db: Session) -> SQLiteProjectRepository:
    return SQLiteProjectRepository(db)


def saved_project(db: Session) -> Project:
    project = Project(title="Test Project", deadline=future(30))
    return make_project_repo(db).save(project)


class TestTaskSave:
    def test_save_creates_new_task(self, db_session: Session):
        repo = make_repo(db_session)
        task = Task(title="New Task", deadline=future())
        saved = repo.save(task)
        assert saved.id == task.id
        assert saved.title == "New Task"

    def test_save_returns_domain_task(self, db_session: Session):
        repo = make_repo(db_session)
        saved = repo.save(Task(title="T", deadline=future()))
        assert isinstance(saved, Task)

    def test_save_updates_existing_task(self, db_session: Session):
        repo = make_repo(db_session)
        task = repo.save(Task(title="Original", deadline=future()))
        task.update(title="Updated")
        updated = repo.save(task)
        assert updated.title == "Updated"
        assert updated.id == task.id

    def test_save_persists_all_fields(self, db_session: Session):
        repo = make_repo(db_session)
        project = saved_project(db_session)
        task = Task(title="Full Task", deadline=future(5), description="details")
        task.assign_to_project(project.id, project.deadline)
        task.mark_complete()
        task.pull_events()
        saved = repo.save(task)
        assert saved.title == "Full Task"
        assert saved.description == "details"
        assert saved.completed is True
        assert saved.project_id == project.id

    def test_save_update_does_not_duplicate(self, db_session: Session):
        repo = make_repo(db_session)
        task = repo.save(Task(title="T", deadline=future()))
        task.update(title="T2")
        repo.save(task)
        all_tasks = repo.find_all()
        assert len(all_tasks) == 1


class TestTaskFindById:
    def test_find_existing_task(self, db_session: Session):
        repo = make_repo(db_session)
        task = repo.save(Task(title="T", deadline=future()))
        found = repo.find_by_id(task.id)
        assert found is not None
        assert found.id == task.id

    def test_find_missing_returns_none(self, db_session: Session):
        repo = make_repo(db_session)
        assert repo.find_by_id(uuid4()) is None

    def test_find_preserves_utc_timezone(self, db_session: Session):
        repo = make_repo(db_session)
        task = repo.save(Task(title="T", deadline=future()))
        found = repo.find_by_id(task.id)
        assert found.deadline.tzinfo == timezone.utc
        assert found.created_at.tzinfo == timezone.utc
        assert found.updated_at.tzinfo == timezone.utc


class TestTaskFindAll:
    def test_returns_all_tasks(self, db_session: Session):
        repo = make_repo(db_session)
        repo.save(Task(title="A", deadline=future()))
        repo.save(Task(title="B", deadline=future()))
        assert len(repo.find_all()) == 2

    def test_empty_db_returns_empty_list(self, db_session: Session):
        assert make_repo(db_session).find_all() == []

    def test_filter_completed_true(self, db_session: Session):
        repo = make_repo(db_session)
        done = Task(title="Done", deadline=future())
        done.mark_complete()
        done.pull_events()
        repo.save(done)
        repo.save(Task(title="Open", deadline=future()))
        results = repo.find_all(completed=True)
        assert len(results) == 1
        assert results[0].completed is True

    def test_filter_completed_false(self, db_session: Session):
        repo = make_repo(db_session)
        done = Task(title="Done", deadline=future())
        done.mark_complete()
        done.pull_events()
        repo.save(done)
        repo.save(Task(title="Open", deadline=future()))
        results = repo.find_all(completed=False)
        assert len(results) == 1
        assert results[0].completed is False

    def test_filter_overdue_true(self, db_session: Session):
        repo = make_repo(db_session)
        overdue = Task(title="Overdue", deadline=past(2))
        repo.save(overdue)
        repo.save(Task(title="Future", deadline=future()))
        results = repo.find_all(overdue=True)
        assert len(results) == 1
        assert results[0].title == "Overdue"

    def test_filter_overdue_excludes_completed(self, db_session: Session):
        repo = make_repo(db_session)
        overdue_but_done = Task(title="Done Overdue", deadline=past(2))
        overdue_but_done.mark_complete()
        overdue_but_done.pull_events()
        repo.save(overdue_but_done)
        results = repo.find_all(overdue=True)
        assert results == []

    def test_filter_overdue_false_includes_completed_and_future(self, db_session: Session):
        repo = make_repo(db_session)
        done = Task(title="Done", deadline=past(1))
        done.mark_complete()
        done.pull_events()
        repo.save(done)
        repo.save(Task(title="Future", deadline=future()))
        repo.save(Task(title="Overdue Open", deadline=past(2)))
        results = repo.find_all(overdue=False)
        titles = {t.title for t in results}
        assert "Done" in titles
        assert "Future" in titles
        assert "Overdue Open" not in titles

    def test_filter_by_project_id(self, db_session: Session):
        repo = make_repo(db_session)
        project = saved_project(db_session)
        linked = Task(title="Linked", deadline=future(5))
        linked.assign_to_project(project.id, project.deadline)
        repo.save(linked)
        repo.save(Task(title="Unlinked", deadline=future()))
        results = repo.find_all(project_id=project.id)
        assert len(results) == 1
        assert results[0].title == "Linked"

    def test_filter_by_nonexistent_project_returns_empty(self, db_session: Session):
        repo = make_repo(db_session)
        repo.save(Task(title="T", deadline=future()))
        assert repo.find_all(project_id=uuid4()) == []


class TestTaskFindByProject:
    def test_returns_project_tasks(self, db_session: Session):
        repo = make_repo(db_session)
        project = saved_project(db_session)
        t1 = Task(title="T1", deadline=future(5))
        t1.assign_to_project(project.id, project.deadline)
        t2 = Task(title="T2", deadline=future(5))
        t2.assign_to_project(project.id, project.deadline)
        repo.save(t1)
        repo.save(t2)
        repo.save(Task(title="Other", deadline=future()))
        results = repo.find_by_project(project.id)
        assert len(results) == 2

    def test_returns_empty_for_unknown_project(self, db_session: Session):
        make_repo(db_session).save(Task(title="T", deadline=future()))
        assert make_repo(db_session).find_by_project(uuid4()) == []


class TestTaskDelete:
    def test_delete_removes_task(self, db_session: Session):
        repo = make_repo(db_session)
        task = repo.save(Task(title="T", deadline=future()))
        repo.delete(task.id)
        assert repo.find_by_id(task.id) is None

    def test_delete_nonexistent_does_not_raise(self, db_session: Session):
        make_repo(db_session).delete(uuid4())  # must not raise

    def test_delete_only_removes_target(self, db_session: Session):
        repo = make_repo(db_session)
        t1 = repo.save(Task(title="Keep", deadline=future()))
        t2 = repo.save(Task(title="Remove", deadline=future()))
        repo.delete(t2.id)
        assert repo.find_by_id(t1.id) is not None
        assert repo.find_by_id(t2.id) is None
