import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import infrastructure.db.orm_models  # noqa: F401
from application.project_service import ProjectService
from application.task_service import TaskService
from application.user_service import UserService
from config import Config
from infrastructure.db.database import Base
from infrastructure.db.project_repository import SQLiteProjectRepository
from infrastructure.db.task_repository import SQLiteTaskRepository
from infrastructure.db.user_repository import SQLiteUserRepository
from infrastructure.notifications.notification_service import NotificationService


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def config():
    cfg = Config()
    cfg.AUTO_COMPLETE_PROJECT = False
    return cfg


@pytest.fixture
def notifications():
    return NotificationService()


@pytest.fixture
def user_service(db_session):
    return UserService(user_repo=SQLiteUserRepository(db_session))


@pytest.fixture
def task_service(db_session, notifications, config):
    return TaskService(
        task_repo=SQLiteTaskRepository(db_session),
        project_repo=SQLiteProjectRepository(db_session),
        user_repo=SQLiteUserRepository(db_session),
        notifications=notifications,
        config=config,
    )


@pytest.fixture
def project_service(db_session, notifications):
    return ProjectService(
        project_repo=SQLiteProjectRepository(db_session),
        task_repo=SQLiteTaskRepository(db_session),
        notifications=notifications,
    )
