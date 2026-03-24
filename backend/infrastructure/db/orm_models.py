"""
SQLAlchemy ORM models — infrastructure detail only.
These are kept strictly separate from the domain models in domain/models/.
The repositories handle all mapping between the two.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from infrastructure.db.database import Base


class UserORM(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    fullname = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    owned_projects = relationship("ProjectORM", back_populates="owner", lazy="select")
    assigned_tasks = relationship("TaskORM", back_populates="assignee", lazy="select")


class ProjectORM(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)
    title = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    tasks = relationship("TaskORM", back_populates="project", lazy="select")
    owner = relationship("UserORM", back_populates="owned_projects")


class TaskORM(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="todo", nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    assignee_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    project = relationship("ProjectORM", back_populates="tasks")
    assignee = relationship("UserORM", back_populates="assigned_tasks")
