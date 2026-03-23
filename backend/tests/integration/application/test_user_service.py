from uuid import uuid4

import pytest

from application.user_service import UserService
from domain.exceptions import UserAlreadyExistsError, UserNotFoundError


class TestCreateUser:
    def test_creates_and_persists_user(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "password")
        assert user.id is not None
        assert user_service.get_user(user.id).email == "alice@example.com"

    def test_stores_hashed_password_not_plaintext(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "secret")
        assert user.password_hash != "secret"

    def test_duplicate_email_raises(self, user_service: UserService):
        user_service.create_user("Alice", "alice@example.com", "pw1")
        with pytest.raises(UserAlreadyExistsError):
            user_service.create_user("Alice2", "alice@example.com", "pw2")

    def test_different_emails_are_allowed(self, user_service: UserService):
        u1 = user_service.create_user("Alice", "alice@example.com", "pw")
        u2 = user_service.create_user("Bob", "bob@example.com", "pw")
        assert u1.id != u2.id


class TestGetUser:
    def test_returns_existing_user(self, user_service: UserService):
        created = user_service.create_user("Alice", "alice@example.com", "pw")
        found = user_service.get_user(created.id)
        assert found.id == created.id
        assert found.fullname == "Alice"

    def test_raises_for_missing_user(self, user_service: UserService):
        with pytest.raises(UserNotFoundError):
            user_service.get_user(uuid4())


class TestGetAllUsers:
    def test_returns_all_users(self, user_service: UserService):
        user_service.create_user("Alice", "alice@example.com", "pw")
        user_service.create_user("Bob", "bob@example.com", "pw")
        assert len(user_service.get_all_users()) == 2

    def test_empty_list_when_no_users(self, user_service: UserService):
        assert user_service.get_all_users() == []


class TestUpdateUser:
    def test_updates_fullname(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        updated = user_service.update_user(user.id, fullname="Alicia")
        assert updated.fullname == "Alicia"

    def test_updates_email(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        updated = user_service.update_user(user.id, email="alicia@example.com")
        assert updated.email == "alicia@example.com"

    def test_update_email_to_existing_email_raises(self, user_service: UserService):
        user_service.create_user("Alice", "alice@example.com", "pw")
        bob = user_service.create_user("Bob", "bob@example.com", "pw")
        with pytest.raises(UserAlreadyExistsError):
            user_service.update_user(bob.id, email="alice@example.com")

    def test_update_email_to_same_email_is_allowed(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        updated = user_service.update_user(user.id, email="alice@example.com")
        assert updated.email == "alice@example.com"

    def test_updates_password_hash(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "oldpw")
        old_hash = user.password_hash
        updated = user_service.update_user(user.id, password="newpw")
        assert updated.password_hash != old_hash

    def test_raises_for_missing_user(self, user_service: UserService):
        with pytest.raises(UserNotFoundError):
            user_service.update_user(uuid4(), fullname="Ghost")


class TestDeleteUser:
    def test_deletes_user(self, user_service: UserService):
        user = user_service.create_user("Alice", "alice@example.com", "pw")
        user_service.delete_user(user.id)
        with pytest.raises(UserNotFoundError):
            user_service.get_user(user.id)

    def test_raises_for_missing_user(self, user_service: UserService):
        with pytest.raises(UserNotFoundError):
            user_service.delete_user(uuid4())
