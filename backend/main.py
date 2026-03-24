import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.exception_handlers import (
    deadline_constraint_handler,
    project_completion_handler,
    project_not_found_handler,
    task_not_found_handler,
    user_already_exists_handler,
    user_not_found_handler,
)
from api.routers import auth, projects, tasks, users
from application.user_service import UserService
from domain.exceptions import (
    DeadlineConstraintError,
    ProjectCompletionError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from infrastructure.db.database import SessionLocal, init_db
from infrastructure.db.user_repository import SQLiteUserRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

DEFAULT_USER_EMAIL = "admin@example.com"
DEFAULT_USER_PASSWORD = "admin123"
DEFAULT_USER_FULLNAME = "Admin User"


def _seed_default_user() -> None:
    db = SessionLocal()
    try:
        service = UserService(SQLiteUserRepository(db))
        users = service.get_all_users()
        if not users:
            user = service.create_user(
                fullname=DEFAULT_USER_FULLNAME,
                email=DEFAULT_USER_EMAIL,
                password=DEFAULT_USER_PASSWORD,
            )
            logger.info(
                "Default user created — email: %s  password: %s  id: %s",
                DEFAULT_USER_EMAIL,
                DEFAULT_USER_PASSWORD,
                user.id,
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    _seed_default_user()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Domain exception → HTTP error mapping ---
app.add_exception_handler(TaskNotFoundError, task_not_found_handler)
app.add_exception_handler(ProjectNotFoundError, project_not_found_handler)
app.add_exception_handler(DeadlineConstraintError, deadline_constraint_handler)
app.add_exception_handler(ProjectCompletionError, project_completion_handler)
app.add_exception_handler(UserNotFoundError, user_not_found_handler)
app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)

# --- Routers ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(projects.router)


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}
