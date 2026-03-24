from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.models.task import Task
from domain.ports.repositories import TaskRepository
from infrastructure.db.orm_models import TaskORM


class SQLiteTaskRepository(TaskRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(row: TaskORM) -> Task:
        return Task(
            id=UUID(row.id),
            title=row.title,
            description=row.description,
            deadline=row.deadline.replace(tzinfo=timezone.utc),
            completed=row.completed,
            status=row.status,
            project_id=UUID(row.project_id) if row.project_id else None,
            assignee_id=UUID(row.assignee_id) if row.assignee_id else None,
            created_at=row.created_at.replace(tzinfo=timezone.utc),
            updated_at=row.updated_at.replace(tzinfo=timezone.utc),
        )

    @staticmethod
    def _to_orm(task: Task) -> TaskORM:
        return TaskORM(
            id=str(task.id),
            title=task.title,
            description=task.description,
            # strip tzinfo — SQLite stores naive UTC datetimes
            deadline=task.deadline.replace(tzinfo=None),
            completed=task.completed,
            status=task.status,
            project_id=str(task.project_id) if task.project_id else None,
            assignee_id=str(task.assignee_id) if task.assignee_id else None,
            created_at=task.created_at.replace(tzinfo=None),
            updated_at=task.updated_at.replace(tzinfo=None),
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def save(self, task: Task) -> Task:
        row = self._db.get(TaskORM, str(task.id))
        if row is None:
            row = self._to_orm(task)
            self._db.add(row)
        else:
            row.title = task.title
            row.description = task.description
            row.deadline = task.deadline.replace(tzinfo=None)
            row.completed = task.completed
            row.status = task.status
            row.project_id = str(task.project_id) if task.project_id else None
            row.assignee_id = str(task.assignee_id) if task.assignee_id else None
            row.updated_at = task.updated_at.replace(tzinfo=None)
        self._db.commit()
        self._db.refresh(row)
        return self._to_domain(row)

    def find_by_id(self, task_id: UUID) -> Optional[Task]:
        row = self._db.get(TaskORM, str(task_id))
        return self._to_domain(row) if row else None

    def find_all(
        self,
        completed: Optional[bool] = None,
        overdue: Optional[bool] = None,
        project_id: Optional[UUID] = None,
    ) -> List[Task]:
        query = self._db.query(TaskORM)

        if completed is not None:
            query = query.filter(TaskORM.completed == completed)

        if overdue is True:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            query = query.filter(TaskORM.deadline < now, TaskORM.completed == False)  # noqa: E712
        elif overdue is False:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            query = query.filter(
                (TaskORM.completed == True) | (TaskORM.deadline >= now)  # noqa: E712
            )

        if project_id is not None:
            query = query.filter(TaskORM.project_id == str(project_id))

        return [self._to_domain(row) for row in query.all()]

    def find_by_project(self, project_id: UUID) -> List[Task]:
        rows = self._db.query(TaskORM).filter(TaskORM.project_id == str(project_id)).all()
        return [self._to_domain(row) for row in rows]

    def delete(self, task_id: UUID) -> None:
        row = self._db.get(TaskORM, str(task_id))
        if row:
            self._db.delete(row)
            self._db.commit()
