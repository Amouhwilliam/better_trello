from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from domain.models.project import Project
from domain.models.task import Task
from domain.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def future(days: int = 7) -> datetime:
    return utc_now() + timedelta(days=days)


def past(days: int = 1) -> datetime:
    return utc_now() - timedelta(days=days)


@pytest.fixture
def project() -> Project:
    return Project(title="Test Project", deadline=future(30))


@pytest.fixture
def task() -> Task:
    return Task(title="Test Task", deadline=future(7))


@pytest.fixture
def task_in_project(project: Project) -> Task:
    t = Task(title="Linked Task", deadline=future(7))
    t.assign_to_project(project.id, project.deadline)
    return t


@pytest.fixture
def user() -> User:
    return User(fullname="Alice Dupont", email="alice@example.com", password_hash="hashed")
