from uuid import uuid4

import pytest

from domain.models.user import User
from infrastructure.db.user_repository import SQLiteUserRepository


def make_user(repo: SQLiteUserRepository, email: str = "alice@example.com") -> User:
    user = User(fullname="Alice", email=email, password_hash="hash")
    return repo.save(user)


class TestSaveUser:
    def test_save_persists_new_user(self, db_session):
        repo = SQLiteUserRepository(db_session)
        user = User(fullname="Alice", email="alice@example.com", password_hash="hash")
        saved = repo.save(user)
        assert saved.id == user.id
        assert saved.email == "alice@example.com"

    def test_save_updates_existing_user(self, db_session):
        repo = SQLiteUserRepository(db_session)
        user = make_user(repo)
        user.update(fullname="Alicia")
        updated = repo.save(user)
        assert updated.fullname == "Alicia"

    def test_saved_user_has_utc_timestamps(self, db_session):
        from datetime import timezone
        repo = SQLiteUserRepository(db_session)
        user = make_user(repo)
        assert user.created_at.tzinfo == timezone.utc
        assert user.updated_at.tzinfo == timezone.utc


class TestFindById:
    def test_returns_user_when_found(self, db_session):
        repo = SQLiteUserRepository(db_session)
        user = make_user(repo)
        found = repo.find_by_id(user.id)
        assert found is not None
        assert found.id == user.id

    def test_returns_none_for_missing_id(self, db_session):
        repo = SQLiteUserRepository(db_session)
        assert repo.find_by_id(uuid4()) is None


class TestFindByEmail:
    def test_returns_user_when_found(self, db_session):
        repo = SQLiteUserRepository(db_session)
        make_user(repo, email="alice@example.com")
        found = repo.find_by_email("alice@example.com")
        assert found is not None
        assert found.email == "alice@example.com"

    def test_returns_none_for_unknown_email(self, db_session):
        repo = SQLiteUserRepository(db_session)
        assert repo.find_by_email("ghost@example.com") is None

    def test_email_lookup_is_case_sensitive(self, db_session):
        repo = SQLiteUserRepository(db_session)
        make_user(repo, email="alice@example.com")
        assert repo.find_by_email("ALICE@EXAMPLE.COM") is None


class TestFindAll:
    def test_returns_all_saved_users(self, db_session):
        repo = SQLiteUserRepository(db_session)
        make_user(repo, email="a@x.com")
        make_user(repo, email="b@x.com")
        assert len(repo.find_all()) == 2

    def test_returns_empty_list_when_no_users(self, db_session):
        repo = SQLiteUserRepository(db_session)
        assert repo.find_all() == []


class TestDeleteUser:
    def test_deletes_existing_user(self, db_session):
        repo = SQLiteUserRepository(db_session)
        user = make_user(repo)
        repo.delete(user.id)
        assert repo.find_by_id(user.id) is None

    def test_delete_nonexistent_user_does_not_raise(self, db_session):
        repo = SQLiteUserRepository(db_session)
        repo.delete(uuid4())  # must not raise
