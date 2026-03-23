from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.models.project import Project
from domain.models.task import Task
from domain.models.user import User

# These are PORTS — abstract contracts that define what persistence operations
# the application needs, with no knowledge of how they are fulfilled.
#
# The concrete implementations (ADAPTERS) live in infrastructure/db/ and handle
# the actual SQLite queries. Depending only on these interfaces means the domain
# and application layers never import SQLAlchemy or any storage detail — you can
# swap the database engine by writing a new adapter without touching domain code.


class TaskRepository(ABC):
    @abstractmethod
    def save(self, task: Task) -> Task: ...

    @abstractmethod
    def find_by_id(self, task_id: UUID) -> Optional[Task]: ...

    @abstractmethod
    def find_all(
        self,
        completed: Optional[bool] = None,
        overdue: Optional[bool] = None,
        project_id: Optional[UUID] = None,
    ) -> List[Task]: ...

    @abstractmethod
    def find_by_project(self, project_id: UUID) -> List[Task]: ...

    @abstractmethod
    def delete(self, task_id: UUID) -> None: ...


class ProjectRepository(ABC):
    @abstractmethod
    def save(self, project: Project) -> Project: ...

    @abstractmethod
    def find_by_id(self, project_id: UUID) -> Optional[Project]: ...

    @abstractmethod
    def find_all(self) -> List[Project]: ...

    @abstractmethod
    def delete(self, project_id: UUID) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def find_by_id(self, user_id: UUID) -> Optional[User]: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def find_all(self) -> List[User]: ...

    @abstractmethod
    def delete(self, user_id: UUID) -> None: ...
