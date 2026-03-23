from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from api.dependencies import get_project_service, get_task_service
from api.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from api.schemas.task import TaskResponse
from application.project_service import ProjectService
from application.task_service import TaskService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects",
)
def list_projects(service: ProjectService = Depends(get_project_service)):
    return [ProjectResponse.from_domain(p) for p in service.get_all_projects()]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID",
)
def get_project(project_id: UUID, service: ProjectService = Depends(get_project_service)):
    return ProjectResponse.from_domain(service.get_project(project_id))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(body: ProjectCreate, service: ProjectService = Depends(get_project_service)):
    return ProjectResponse.from_domain(
        service.create_project(title=body.title, deadline=body.deadline, owner_id=body.owner_id)
    )


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    description=(
        "Update title and/or deadline. "
        "If the new deadline is earlier than the current one, any task deadlines that would exceed it "
        "are automatically clamped to the new project deadline."
    ),
)
def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
):
    return ProjectResponse.from_domain(
        service.update_project(project_id=project_id, title=body.title, deadline=body.deadline)
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
def delete_project(project_id: UUID, service: ProjectService = Depends(get_project_service)):
    service.delete_project(project_id)


@router.patch(
    "/{project_id}/complete",
    response_model=ProjectResponse,
    summary="Mark a project as completed",
    description="All tasks in the project must be completed first, otherwise a 422 is returned.",
)
def complete_project(project_id: UUID, service: ProjectService = Depends(get_project_service)):
    return ProjectResponse.from_domain(service.complete_project(project_id))


@router.get(
    "/{project_id}/tasks",
    response_model=List[TaskResponse],
    summary="List all tasks for a project",
)
def get_project_tasks(project_id: UUID, service: ProjectService = Depends(get_project_service)):
    return [TaskResponse.from_domain(t) for t in service.get_project_tasks(project_id)]


@router.post(
    "/{project_id}/tasks/{task_id}/link",
    response_model=TaskResponse,
    summary="Link a task to a project",
    description="Associates the task with the project. The task's deadline must not exceed the project's deadline.",
)
def link_task(
    project_id: UUID,
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
):
    return TaskResponse.from_domain(task_service.link_task_to_project(task_id, project_id))


@router.delete(
    "/{project_id}/tasks/{task_id}/unlink",
    response_model=TaskResponse,
    summary="Unlink a task from a project",
)
def unlink_task(
    project_id: UUID,
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
):
    return TaskResponse.from_domain(task_service.unlink_task_from_project(task_id, project_id))
