from datetime import datetime
from typing import List, Optional
from uuid import UUID

from domain.events import ProjectDeadlineUpdated
from domain.exceptions import ProjectNotFoundError
from domain.models.project import Project
from domain.models.task import Task
from domain.ports.notification_port import NotificationPort
from domain.ports.repositories import ProjectRepository, TaskRepository


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        notifications: NotificationPort,
    ) -> None:
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._notifications = notifications

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_project(self, project_id: UUID) -> Project:
        project = self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return project

    def get_all_projects(self) -> List[Project]:
        return self._project_repo.find_all()

    def get_project_tasks(self, project_id: UUID) -> List[Task]:
        self.get_project(project_id)  # raises if not found
        return self._task_repo.find_by_project(project_id)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_project(self, title: str, deadline: datetime, owner_id: Optional[UUID] = None) -> Project:
        project = Project(title=title, deadline=deadline, owner_id=owner_id)
        return self._project_repo.save(project)

    def update_project(
        self,
        project_id: UUID,
        title: Optional[str] = None,
        deadline: Optional[datetime] = None,
        auto_complete: Optional[bool] = None,
    ) -> Project:
        project = self.get_project(project_id)
        tasks = self._task_repo.find_by_project(project_id)

        if auto_complete is not None:
            project.auto_complete = auto_complete
        project.update(title=title, deadline=deadline, tasks=tasks)
        saved = self._project_repo.save(project)

        events = project.pull_events()

        # Handle ProjectDeadlineUpdated — clamp affected task deadlines to the new project deadline
        for event in events:
            if isinstance(event, ProjectDeadlineUpdated):
                for task_id in event.affected_task_ids:
                    task = self._task_repo.find_by_id(task_id)
                    if task:
                        task.adjust_deadline(event.new_deadline)
                        self._task_repo.save(task)

        self._notifications.dispatch_all(events)
        return saved

    def complete_project(self, project_id: UUID) -> Project:
        project = self.get_project(project_id)
        tasks = self._task_repo.find_by_project(project_id)
        project.mark_complete(tasks)  # raises ProjectCompletionError if tasks are open
        saved = self._project_repo.save(project)
        self._notifications.dispatch_all(project.pull_events())
        return saved

    def delete_project(self, project_id: UUID) -> None:
        self.get_project(project_id)  # raises ProjectNotFoundError if missing
        self._project_repo.delete(project_id)
