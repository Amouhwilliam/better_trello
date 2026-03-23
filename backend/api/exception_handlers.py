from fastapi import Request
from fastapi.responses import JSONResponse

from domain.exceptions import (
    DeadlineConstraintError,
    ProjectCompletionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def project_not_found_handler(request: Request, exc: ProjectNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def deadline_constraint_handler(request: Request, exc: DeadlineConstraintError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def project_completion_handler(request: Request, exc: ProjectCompletionError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def user_not_found_handler(request: Request, exc: UserNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
