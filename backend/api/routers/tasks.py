from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from api.dependencies import get_task_service
from api.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from application.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get(
    "",
    response_model=List[TaskResponse],
    summary="List all tasks",
    description="Returns all tasks. Optionally filter by completion status, overdue state, or project.",
)
def list_tasks(
    completed: Optional[bool] = None,
    overdue: Optional[bool] = None,
    project_id: Optional[UUID] = None,
    service: TaskService = Depends(get_task_service),
):
    tasks = service.get_all_tasks(completed=completed, overdue=overdue, project_id=project_id)
    return [TaskResponse.from_domain(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
)
def get_task(task_id: UUID, service: TaskService = Depends(get_task_service)):
    return TaskResponse.from_domain(service.get_task(task_id))


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
def create_task(body: TaskCreate, service: TaskService = Depends(get_task_service)):
    task = service.create_task(
        title=body.title,
        deadline=body.deadline,
        description=body.description,
    )
    return TaskResponse.from_domain(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    description="Update title, description, and/or deadline. To change completion state use the /complete or /reopen endpoints.",
)
def update_task(
    task_id: UUID,
    body: TaskUpdate,
    service: TaskService = Depends(get_task_service),
):
    task = service.update_task(
        task_id=task_id,
        title=body.title,
        description=body.description,
        deadline=body.deadline,
    )
    return TaskResponse.from_domain(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
)
def delete_task(task_id: UUID, service: TaskService = Depends(get_task_service)):
    service.delete_task(task_id)


@router.patch(
    "/{task_id}/complete",
    response_model=TaskResponse,
    summary="Mark a task as completed",
)
def complete_task(task_id: UUID, service: TaskService = Depends(get_task_service)):
    return TaskResponse.from_domain(service.complete_task(task_id))


@router.patch(
    "/{task_id}/reopen",
    response_model=TaskResponse,
    summary="Reopen a completed task",
    description="Sets the task back to incomplete. If the parent project was completed, it will also be set back to open.",
)
def reopen_task(task_id: UUID, service: TaskService = Depends(get_task_service)):
    return TaskResponse.from_domain(service.reopen_task(task_id))
