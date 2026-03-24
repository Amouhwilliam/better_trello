import hashlib
from typing import List, Optional
from uuid import UUID

from domain.exceptions import UserAlreadyExistsError, UserNotFoundError
from domain.models.user import User
from domain.ports.repositories import UserRepository


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_user(self, user_id: UUID) -> User:
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")
        return user

    def get_all_users(self) -> List[User]:
        return self._user_repo.find_all()

    def get_user_by_email(self, email: str) -> User:
        user = self._user_repo.find_by_email(email)
        if user is None:
            raise UserNotFoundError(f"User with email '{email}' not found")
        return user

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_user(self, fullname: str, email: str, password: str) -> User:
        if self._user_repo.find_by_email(email) is not None:
            raise UserAlreadyExistsError(f"A user with email '{email}' already exists")
        user = User(fullname=fullname, email=email, password_hash=_hash_password(password))
        return self._user_repo.save(user)

    def update_user(
        self,
        user_id: UUID,
        fullname: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ) -> User:
        user = self.get_user(user_id)
        if email is not None and email != user.email:
            if self._user_repo.find_by_email(email) is not None:
                raise UserAlreadyExistsError(f"A user with email '{email}' already exists")
        user.update(fullname=fullname, email=email)
        if password is not None:
            user.update_password(_hash_password(password))
        return self._user_repo.save(user)

    def delete_user(self, user_id: UUID) -> None:
        self.get_user(user_id)  # raises UserNotFoundError if missing
        self._user_repo.delete(user_id)
