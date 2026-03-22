from datetime import timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from domain.models.project import Project
from infrastructure.db.project_repository import SQLiteProjectRepository
from tests.conftest import future, past


def make_repo(db: Session) -> SQLiteProjectRepository:
    return SQLiteProjectRepository(db)


class TestProjectSave:
    def test_save_creates_new_project(self, db_session: Session):
        repo = make_repo(db_session)
        project = Project(title="My Project", deadline=future(30))
        saved = repo.save(project)
        assert saved.id == project.id
        assert saved.title == "My Project"

    def test_save_returns_domain_project(self, db_session: Session):
        saved = make_repo(db_session).save(Project(title="P", deadline=future()))
        assert isinstance(saved, Project)

    def test_save_updates_existing_project(self, db_session: Session):
        repo = make_repo(db_session)
        project = repo.save(Project(title="Original", deadline=future(30)))
        project.update(title="Renamed")
        updated = repo.save(project)
        assert updated.title == "Renamed"
        assert updated.id == project.id

    def test_save_persists_all_fields(self, db_session: Session):
        repo = make_repo(db_session)
        project = Project(title="Full", deadline=future(10))
        project.mark_complete([])
        project.pull_events()
        saved = repo.save(project)
        assert saved.completed is True
        assert saved.title == "Full"

    def test_save_update_does_not_duplicate(self, db_session: Session):
        repo = make_repo(db_session)
        project = repo.save(Project(title="P", deadline=future()))
        project.update(title="P2")
        repo.save(project)
        assert len(repo.find_all()) == 1


class TestProjectFindById:
    def test_find_existing_project(self, db_session: Session):
        repo = make_repo(db_session)
        project = repo.save(Project(title="P", deadline=future()))
        found = repo.find_by_id(project.id)
        assert found is not None
        assert found.id == project.id

    def test_find_missing_returns_none(self, db_session: Session):
        assert make_repo(db_session).find_by_id(uuid4()) is None

    def test_find_preserves_utc_timezone(self, db_session: Session):
        repo = make_repo(db_session)
        project = repo.save(Project(title="P", deadline=future()))
        found = repo.find_by_id(project.id)
        assert found.deadline.tzinfo == timezone.utc
        assert found.created_at.tzinfo == timezone.utc
        assert found.updated_at.tzinfo == timezone.utc

    def test_find_preserves_deadline_value(self, db_session: Session):
        repo = make_repo(db_session)
        deadline = future(15)
        project = repo.save(Project(title="P", deadline=deadline))
        found = repo.find_by_id(project.id)
        # compare without sub-second precision (SQLite truncates microseconds)
        assert found.deadline.replace(microsecond=0) == deadline.replace(microsecond=0)


class TestProjectFindAll:
    def test_returns_all_projects(self, db_session: Session):
        repo = make_repo(db_session)
        repo.save(Project(title="A", deadline=future()))
        repo.save(Project(title="B", deadline=future()))
        assert len(repo.find_all()) == 2

    def test_empty_db_returns_empty_list(self, db_session: Session):
        assert make_repo(db_session).find_all() == []

    def test_returns_domain_project_instances(self, db_session: Session):
        repo = make_repo(db_session)
        repo.save(Project(title="P", deadline=future()))
        results = repo.find_all()
        assert all(isinstance(p, Project) for p in results)


class TestProjectDelete:
    def test_delete_removes_project(self, db_session: Session):
        repo = make_repo(db_session)
        project = repo.save(Project(title="P", deadline=future()))
        repo.delete(project.id)
        assert repo.find_by_id(project.id) is None

    def test_delete_nonexistent_does_not_raise(self, db_session: Session):
        make_repo(db_session).delete(uuid4())  # must not raise

    def test_delete_only_removes_target(self, db_session: Session):
        repo = make_repo(db_session)
        p1 = repo.save(Project(title="Keep", deadline=future()))
        p2 = repo.save(Project(title="Remove", deadline=future()))
        repo.delete(p2.id)
        assert repo.find_by_id(p1.id) is not None
        assert repo.find_by_id(p2.id) is None
