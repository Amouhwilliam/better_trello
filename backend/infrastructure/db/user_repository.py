from datetime import timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.models.user import User
from domain.ports.repositories import UserRepository
from infrastructure.db.orm_models import UserORM


class SQLiteUserRepository(UserRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(row: UserORM) -> User:
        return User(
            id=UUID(row.id),
            fullname=row.fullname,
            email=row.email,
            password_hash=row.password_hash,
            created_at=row.created_at.replace(tzinfo=timezone.utc),
            updated_at=row.updated_at.replace(tzinfo=timezone.utc),
        )

    @staticmethod
    def _to_orm(user: User) -> UserORM:
        return UserORM(
            id=str(user.id),
            fullname=user.fullname,
            email=user.email,
            password_hash=user.password_hash,
            created_at=user.created_at.replace(tzinfo=None),
            updated_at=user.updated_at.replace(tzinfo=None),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def save(self, user: User) -> User:
        row = self._db.get(UserORM, str(user.id))
        if row is None:
            row = self._to_orm(user)
            self._db.add(row)
        else:
            row.fullname = user.fullname
            row.email = user.email
            row.password_hash = user.password_hash
            row.updated_at = user.updated_at.replace(tzinfo=None)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def find_by_id(self, user_id: UUID) -> Optional[User]:
        row = self._db.get(UserORM, str(user_id))
        return self._to_domain(row) if row else None

    def find_by_email(self, email: str) -> Optional[User]:
        row = self._db.query(UserORM).filter(UserORM.email == email).first()
        return self._to_domain(row) if row else None

    def find_all(self) -> List[User]:
        rows = self._db.query(UserORM).all()
        return [self._to_domain(row) for row in rows]

    def delete(self, user_id: UUID) -> None:
        row = self._db.get(UserORM, str(user_id))
        if row:
            self._db.delete(row)
            self._db.commit()
