from datetime import timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.models.project import Project
from domain.ports.repositories import ProjectRepository
from infrastructure.db.orm_models import ProjectORM


class SQLiteProjectRepository(ProjectRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(row: ProjectORM) -> Project:
        return Project(
            id=UUID(row.id),
            title=row.title,
            deadline=row.deadline.replace(tzinfo=timezone.utc),
            completed=row.completed,
            owner_id=UUID(row.owner_id) if row.owner_id else None,
            created_at=row.created_at.replace(tzinfo=timezone.utc),
            updated_at=row.updated_at.replace(tzinfo=timezone.utc),
        )

    @staticmethod
    def _to_orm(project: Project) -> ProjectORM:
        return ProjectORM(
            id=str(project.id),
            title=project.title,
            deadline=project.deadline.replace(tzinfo=None),
            completed=project.completed,
            owner_id=str(project.owner_id) if project.owner_id else None,
            created_at=project.created_at.replace(tzinfo=None),
            updated_at=project.updated_at.replace(tzinfo=None),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def save(self, project: Project) -> Project:
        row = self._db.get(ProjectORM, str(project.id))
        if row is None:
            row = self._to_orm(project)
            self._db.add(row)
        else:
            row.title = project.title
            row.deadline = project.deadline.replace(tzinfo=None)
            row.completed = project.completed
            row.owner_id = str(project.owner_id) if project.owner_id else None
            row.updated_at = project.updated_at.replace(tzinfo=None)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def find_by_id(self, project_id: UUID) -> Optional[Project]:
        row = self._db.get(ProjectORM, str(project_id))
        return self._to_domain(row) if row else None

    def find_all(self) -> List[Project]:
        rows = self._db.query(ProjectORM).all()
        return [self._to_domain(row) for row in rows]

    def delete(self, project_id: UUID) -> None:
        row = self._db.get(ProjectORM, str(project_id))
        if row:
            self._db.delete(row)
            self._db.commit()
