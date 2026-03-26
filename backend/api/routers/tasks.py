from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from api.dependencies import get_current_user_id, get_task_service
from api.schemas.task import PaginatedTasksResponse, TaskCreate, TaskResponse, TaskUpdate
from application.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get(
    "",
    response_model=PaginatedTasksResponse,
    summary="List tasks (paginated)",
    description="Returns a paginated list of tasks. Supports filtering by completion status, overdue state, or project.",
)
def list_tasks(
    completed: Optional[bool] = None,
    overdue: Optional[bool] = None,
    project_id: Optional[UUID] = None,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(15, ge=1, le=100, description="Number of tasks per page"),
    service: TaskService = Depends(get_task_service),
    _: UUID = Depends(get_current_user_id),
):
    all_tasks = service.get_all_tasks(completed=completed, overdue=overdue, project_id=project_id)
    total = len(all_tasks)
    skip = (page - 1) * page_size
    items = all_tasks[skip : skip + page_size]
    return PaginatedTasksResponse(
        items=[TaskResponse.from_domain(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get a task by ID",
)
def get_task(task_id: UUID, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    return TaskResponse.from_domain(service.get_task(task_id))


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
)
def create_task(body: TaskCreate, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    task = service.create_task(
        title=body.title,
        deadline=body.deadline,
        description=body.description,
        project_id=body.project_id,
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
    _: UUID = Depends(get_current_user_id),
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
def delete_task(task_id: UUID, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    service.delete_task(task_id)


@router.patch(
    "/{task_id}/complete",
    response_model=TaskResponse,
    summary="Mark a task as completed",
)
def complete_task(task_id: UUID, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    return TaskResponse.from_domain(service.complete_task(task_id))


@router.patch(
    "/{task_id}/reopen",
    response_model=TaskResponse,
    summary="Reopen a completed task",
    description="Sets the task back to incomplete. If the parent project was completed, it will also be set back to open.",
)
def reopen_task(task_id: UUID, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    return TaskResponse.from_domain(service.reopen_task(task_id))


class TaskStatusUpdate(BaseModel):
    status: str  # "todo" | "in_progress" | "completed"


@router.patch("/{task_id}/status", response_model=TaskResponse, summary="Update task status")
def update_task_status(task_id: UUID, body: TaskStatusUpdate, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    return TaskResponse.from_domain(service.update_task_status(task_id, body.status))


@router.patch(
    "/{task_id}/assign/{user_id}",
    response_model=TaskResponse,
    summary="Assign a user to a task",
    description="Sets the task's assignee. A task can have at most one assignee at a time.",
)
def assign_task(
    task_id: UUID,
    user_id: UUID,
    service: TaskService = Depends(get_task_service),
    _: UUID = Depends(get_current_user_id),
):
    return TaskResponse.from_domain(service.assign_task_to_user(task_id, user_id))


@router.patch(
    "/{task_id}/unassign",
    response_model=TaskResponse,
    summary="Remove the assignee from a task",
)
def unassign_task(task_id: UUID, service: TaskService = Depends(get_task_service), _: UUID = Depends(get_current_user_id)):
    return TaskResponse.from_domain(service.unassign_task(task_id))
