# Better Trello

A full-stack task management application inspired by Trello. Built as a PAYBACK coding challenge with a strong focus on software architecture, clean separation of concerns, and test coverage.

---

## Stack

| Layer       | Technology                                              |
|-------------|---------------------------------------------------------|
| Frontend    | Next.js 15 (App Router), TypeScript, Tailwind CSS       |
| Backend     | FastAPI, Python 3.12, SQLAlchemy 2, SQLite              |
| Auth        | JWT (PyJWT), HTTP-only cookie on the frontend           |
| Testing     | pytest, 349 tests (unit · integration · functional)     |
| Runtime     | Docker, Docker Compose                                  |
| DB Browser  | Datasette (port 8081)                                   |

---

## Project Structure

```
better_trello/
├── backend/               # FastAPI backend (Hexagonal Architecture)
│   ├── domain/            # Pure business logic — no frameworks
│   ├── application/       # Use-case services
│   ├── infrastructure/    # SQLite repositories, notification adapters
│   ├── api/               # FastAPI routers, schemas, dependency injection
│   ├── tests/             # Unit, integration, and functional test suites
│   └── main.py            # App entrypoint with lifespan
├── frontend/              # Next.js 15 App Router frontend
│   ├── app/               # Pages and API routes
│   └── lib/               # Typed API client
├── docker-compose.yml
└── DESIGN.md              # Architecture & design decisions
```

---

## Running the App

### Start everything

```bash
docker compose up --build
```

| Service        | URL                         |
|----------------|-----------------------------|
| Frontend       | http://localhost:3000       |
| API            | http://localhost:8000       |
| API Docs       | http://localhost:8000/docs  |
| Datasette (DB) | http://localhost:8081       |

A default admin user is seeded on first start:

| Field    | Value               |
|----------|---------------------|
| Email    | admin@example.com   |
| Password | admin123            |
| Name     | Admin User          |

### Stop all services

```bash
docker compose down
```

---

## Development

### Backend (FastAPI)

```bash
cd backend

# Create virtual environment (one-time)
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv

# Run dev server
source .venv/bin/activate
uvicorn main:app --reload
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

---

## Testing

### Setup (one-time)

Install [uv](https://github.com/astral-sh/uv) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create the virtual environment and install all dependencies:

```bash
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv
```

### Run all tests

```bash
cd backend
NOTIFICATION_LOG_PATH=/tmp/notifications.log .venv/bin/python -m pytest tests/ -v
```

Or activate the venv first:

```bash
source backend/.venv/bin/activate
cd backend
NOTIFICATION_LOG_PATH=/tmp/notifications.log pytest tests/ -v
```

### Run by layer

```bash
# Unit tests only (no DB, no HTTP)
pytest tests/unit -v

# Integration tests (real SQLite, in-memory)
pytest tests/integration -v

# Functional tests (full HTTP stack, isolated temp DB)
NOTIFICATION_LOG_PATH=/tmp/notifications.log pytest tests/functional -v

# Against a live running server
API_URL=http://localhost:8000 pytest tests/functional -v
```

### Test summary (349 tests)

```
backend/tests/
├── conftest.py                                  # shared fixtures & date helpers
├── unit/
│   ├── domain/
│   │   ├── test_task.py                         # Task model — creation, update,
│   │   │                                        #   assignment, completion, events
│   │   ├── test_project.py                      # Project model — deadline events,
│   │   │                                        #   completion lifecycle, auto-complete
│   │   └── test_user.py                         # User model
│   └── infrastructure/
│       ├── test_notification_service.py
│       ├── test_file_notification_service.py
│       └── test_composite_notification_service.py
├── integration/
│   ├── infrastructure/
│   │   ├── test_task_repository.py
│   │   ├── test_project_repository.py
│   │   └── test_user_repository.py
│   └── application/
│       ├── test_task_service.py                 # 40+ scenarios incl. auto-complete,
│       │                                        #   deadline constraints, assign/unassign
│       ├── test_project_service.py
│       └── test_user_service.py
└── functional/
    ├── test_auth_api.py
    ├── test_tasks_api.py
    ├── test_projects_api.py
    └── test_users_api.py                        # incl. GET /users/me
```

| Area | Tests |
|---|---|
| Task creation, update, deadline validation | `TestTaskCreation`, `TestTaskUpdate` |
| Task ↔ Project association, deadline constraint | `TestTaskProjectAssociation`, `TestLinkAndUnlink` |
| `mark_complete` / `reopen` lifecycle & events | `TestCompleteTask`, `TestReopenTask` |
| Status transitions (todo / in_progress / completed) | `TestUpdateTaskStatus` |
| Assign / unassign user to task | `TestAssignTask` |
| Auto-complete project when last task done | `TestCompleteTask.test_auto_complete_*` |
| Project deadline update → task deadline clamping | `TestProjectUpdate` |
| `mark_complete` guards (all tasks must be done) | `TestProjectCompletion` |
| Notification service (console + file + composite) | `test_notification_service.py` |
| Repository CRUD (SQLite) | `test_task_repository.py`, `test_project_repository.py` |
| Full HTTP stack (routing → DB) | `tests/functional/` |
| JWT auth & `GET /users/me` | `test_auth_api.py`, `test_users_api.py` |

---

## API Overview

```
Auth
  POST   /auth/login

Users
  GET    /users/me
  GET    /users
  GET    /users/{id}
  POST   /users
  PUT    /users/{id}
  DELETE /users/{id}

Tasks
  GET    /tasks                          ?completed= &overdue= &project_id=
  GET    /tasks/{id}
  POST   /tasks
  PUT    /tasks/{id}
  DELETE /tasks/{id}
  PATCH  /tasks/{id}/complete
  PATCH  /tasks/{id}/status
  PATCH  /tasks/{id}/assign/{user_id}
  PATCH  /tasks/{id}/unassign

Projects
  GET    /projects
  GET    /projects/{id}
  POST   /projects
  PUT    /projects/{id}
  DELETE /projects/{id}
  PATCH  /projects/{id}/complete
  GET    /projects/{id}/tasks
  POST   /projects/{id}/tasks/{task_id}/link
  DELETE /projects/{id}/tasks/{task_id}/unlink
```

Full interactive docs at `http://localhost:8000/docs`.

---

## Architecture

See [DESIGN.md](./DESIGN.md) for a detailed breakdown of the backend Hexagonal Architecture and frontend design patterns.
