from datetime import datetime
from typing import List, Optional
from uuid import UUID

from config import Config
from domain.events import TaskReopened
from domain.exceptions import ProjectNotFoundError, TaskNotFoundError, UserNotFoundError
from domain.models.task import Task
from domain.ports.repositories import ProjectRepository, TaskRepository, UserRepository
from infrastructure.notifications.notification_service import NotificationService


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        notifications: NotificationService,
        config: Config,
    ) -> None:
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._notifications = notifications
        self._config = config

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_task(self, task_id: UUID) -> Task:
        task = self._task_repo.find_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task

    def get_all_tasks(
        self,
        completed: Optional[bool] = None,
        overdue: Optional[bool] = None,
        project_id: Optional[UUID] = None,
    ) -> List[Task]:
        return self._task_repo.find_all(
            completed=completed, overdue=overdue, project_id=project_id
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_task(
        self,
        title: str,
        deadline: datetime,
        description: Optional[str] = None,
        project_id: Optional[UUID] = None,
    ) -> Task:
        task = Task(title=title, deadline=deadline, description=description)
        if project_id is not None:
            project = self._project_repo.find_by_id(project_id)
            if project is None:
                raise ProjectNotFoundError(f"Project {project_id} not found")
            task.assign_to_project(project_id, project.deadline)
        saved = self._task_repo.save(task)
        self._notifications.check_deadline_approaching(saved)
        return saved

    def update_task_status(self, task_id: UUID, status: str) -> Task:
        task = self.get_task(task_id)
        if status == "completed":
            task.mark_complete()
        elif status == "todo":
            task.reopen()
        elif status == "in_progress":
            task.set_in_progress()
        saved = self._task_repo.save(task)
        self._notifications.dispatch_all(task.pull_events())
        return saved

    def update_task(
        self,
        task_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ) -> Task:
        task = self.get_task(task_id)

        project_deadline = None
        if task.project_id and deadline is not None:
            project = self._project_repo.find_by_id(task.project_id)
            if project:
                project_deadline = project.deadline

        task.update(title=title, description=description, deadline=deadline, project_deadline=project_deadline)
        saved = self._task_repo.save(task)

        if deadline is not None:
            self._notifications.check_deadline_approaching(saved)

        return saved

    def delete_task(self, task_id: UUID) -> None:
        self.get_task(task_id)  # raises TaskNotFoundError if missing
        self._task_repo.delete(task_id)

    def complete_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.mark_complete()
        saved = self._task_repo.save(task)
        self._notifications.dispatch_all(task.pull_events())

        # If the task belongs to a project, attempt auto-completion
        if saved.project_id:
            self._try_auto_complete_project(saved.project_id)

        return saved

    def reopen_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.reopen()
        saved = self._task_repo.save(task)

        events = task.pull_events()
        self._notifications.dispatch_all(events)

        # Re-opening a task in a completed project sets the project back to open
        for event in events:
            if isinstance(event, TaskReopened) and event.project_id:
                project = self._project_repo.find_by_id(event.project_id)
                if project and project.completed:
                    project.reopen()
                    self._project_repo.save(project)

        return saved

    def link_task_to_project(self, task_id: UUID, project_id: UUID) -> Task:
        task = self.get_task(task_id)
        project = self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} not found")

        task.assign_to_project(project.id, project.deadline)
        return self._task_repo.save(task)

    def unlink_task_from_project(self, task_id: UUID, project_id: UUID) -> Task:
        task = self.get_task(task_id)
        # domain model allows unlinking regardless — just clear the association
        task.unlink_from_project()
        return self._task_repo.save(task)

    def assign_task_to_user(self, task_id: UUID, user_id: UUID) -> Task:
        task = self.get_task(task_id)
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")
        task.assign_to_user(user.id)
        return self._task_repo.save(task)

    def unassign_task(self, task_id: UUID) -> Task:
        task = self.get_task(task_id)
        task.unassign()
        return self._task_repo.save(task)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_auto_complete_project(self, project_id: UUID) -> None:
        project = self._project_repo.find_by_id(project_id)
        if project is None or project.completed:
            return
        project_tasks = self._task_repo.find_by_project(project_id)
        project.try_auto_complete(project_tasks, self._config.AUTO_COMPLETE_PROJECT)
        project_events = project.pull_events()
        if project_events:
            self._project_repo.save(project)
            self._notifications.dispatch_all(project_events)
