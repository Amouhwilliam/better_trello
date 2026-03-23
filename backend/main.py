import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.exception_handlers import (
    deadline_constraint_handler,
    project_completion_handler,
    project_not_found_handler,
    task_not_found_handler,
    user_already_exists_handler,
    user_not_found_handler,
)
from api.routers import projects, tasks, users
from domain.exceptions import (
    DeadlineConstraintError,
    ProjectCompletionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from infrastructure.db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Better Trello API",
    description=(
        "A task management API with projects, deadlines, and completion lifecycle. "
        "Built with Hexagonal Architecture (Ports & Adapters)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --- Domain exception → HTTP error mapping ---
app.add_exception_handler(TaskNotFoundError, task_not_found_handler)
app.add_exception_handler(ProjectNotFoundError, project_not_found_handler)
app.add_exception_handler(DeadlineConstraintError, deadline_constraint_handler)
app.add_exception_handler(ProjectCompletionError, project_completion_handler)
app.add_exception_handler(UserNotFoundError, user_not_found_handler)
app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)

# --- Routers ---
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(projects.router)


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}
