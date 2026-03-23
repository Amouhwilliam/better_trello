from datetime import timezone

from domain.models.user import User
from tests.conftest import utc_now


class TestUserCreation:
    def test_defaults(self):
        user = User(fullname="Alice", email="alice@example.com", password_hash="hash")
        assert user.fullname == "Alice"
        assert user.email == "alice@example.com"
        assert user.password_hash == "hash"
        assert user.id is not None
        assert user.created_at.tzinfo == timezone.utc
        assert user.updated_at.tzinfo == timezone.utc

    def test_unique_ids(self):
        u1 = User(fullname="A", email="a@x.com", password_hash="h")
        u2 = User(fullname="B", email="b@x.com", password_hash="h")
        assert u1.id != u2.id


class TestUserUpdate:
    def test_update_fullname(self, user: User):
        user.update(fullname="Bob Martin")
        assert user.fullname == "Bob Martin"

    def test_update_email(self, user: User):
        user.update(email="bob@example.com")
        assert user.email == "bob@example.com"

    def test_update_both_fields(self, user: User):
        user.update(fullname="Bob", email="bob@example.com")
        assert user.fullname == "Bob"
        assert user.email == "bob@example.com"

    def test_update_none_args_changes_nothing(self, user: User):
        original_name = user.fullname
        original_email = user.email
        user.update()
        assert user.fullname == original_name
        assert user.email == original_email

    def test_update_sets_updated_at(self, user: User):
        before = user.updated_at
        user.update(fullname="New Name")
        assert user.updated_at >= before


class TestUserUpdatePassword:
    def test_update_password_hash(self, user: User):
        user.update_password("new_hash")
        assert user.password_hash == "new_hash"

    def test_update_password_sets_updated_at(self, user: User):
        before = user.updated_at
        user.update_password("new_hash")
        assert user.updated_at >= before
