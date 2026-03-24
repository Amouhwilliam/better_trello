from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from application.project_service import ProjectService
from application.task_service import TaskService
from application.user_service import UserService
from config import config
from infrastructure.db.database import get_db
from infrastructure.db.project_repository import SQLiteProjectRepository
from infrastructure.db.task_repository import SQLiteTaskRepository
from infrastructure.db.user_repository import SQLiteUserRepository
from infrastructure.notifications.composite_notification_service import CompositeNotificationService
from infrastructure.notifications.file_notification_service import FileNotificationService
from infrastructure.notifications.notification_service import NotificationService

# Build once at module load — file handler is shared across requests
_notification_service = CompositeNotificationService(
    NotificationService(),
    FileNotificationService(config.NOTIFICATION_LOG_PATH),
)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(user_repo=SQLiteUserRepository(db))


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(
        task_repo=SQLiteTaskRepository(db),
        project_repo=SQLiteProjectRepository(db),
        user_repo=SQLiteUserRepository(db),
        notifications=_notification_service,
        config=config,
    )


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(
        project_repo=SQLiteProjectRepository(db),
        task_repo=SQLiteTaskRepository(db),
        notifications=_notification_service,
    )


_security = HTTPBearer()

SECRET_KEY = config.JWT_SECRET
ALGORITHM = config.JWT_ALGORITHM


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> UUID:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return UUID(user_id)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
