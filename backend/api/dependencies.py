from fastapi import Depends
from sqlalchemy.orm import Session

from application.project_service import ProjectService
from application.task_service import TaskService
from config import config
from infrastructure.db.database import get_db
from infrastructure.db.project_repository import SQLiteProjectRepository
from infrastructure.db.task_repository import SQLiteTaskRepository
from infrastructure.notifications.notification_service import NotificationService


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(
        task_repo=SQLiteTaskRepository(db),
        project_repo=SQLiteProjectRepository(db),
        notifications=NotificationService(),
        config=config,
    )


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(
        project_repo=SQLiteProjectRepository(db),
        task_repo=SQLiteTaskRepository(db),
        notifications=NotificationService(),
    )
