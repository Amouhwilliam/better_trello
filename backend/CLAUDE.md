# API — Better Trello (PAYBACK Coding Challenge)

## Goal
Build a task management backend that handles tasks, projects, deadlines, and completion lifecycle. The code is evaluated on architecture quality, not just functionality.

---

## Architecture: Hexagonal (Ports & Adapters)

The core business logic must be **framework-agnostic**. FastAPI is only the delivery mechanism.

```
api/
├── domain/               # Pure Python — no FastAPI, no SQLite, no I/O
│   ├── models/           # Task, Project entities + domain rules
│   ├── events/           # Domain events (TaskCompleted, ProjectDeadlineUpdated, ...)
│   ├── exceptions/       # Domain-specific exceptions
│   └── ports/            # Abstract interfaces (repositories, services)
│
├── application/          # Use cases / application services
│   ├── task_service.py
│   └── project_service.py
│
├── infrastructure/       # Adapters — concrete implementations
│   ├── db/               # SQLite via SQLAlchemy (repository implementations)
│   └── notifications/    # In-memory notification/logging service
│
├── api/                  # FastAPI layer (routers, schemas, dependency injection)
│   ├── routers/
│   └── schemas/
│
├── config.py             # App configuration (e.g. auto_complete_project flag)
└── main.py               # FastAPI app entrypoint
```

---

## Data Models

### Task
| Field        | Type     | Notes                        |
|--------------|----------|------------------------------|
| id           | UUID     | Primary key                  |
| title        | string   | Required                     |
| description  | string   | Optional                     |
| deadline     | datetime | Required                     |
| completed    | bool     | Default: False               |
| project_id   | UUID     | FK to Project, nullable      |
| created_at   | datetime | Auto                         |
| updated_at   | datetime | Auto                         |

### Project
| Field        | Type     | Notes                        |
|--------------|----------|------------------------------|
| id           | UUID     | Primary key                  |
| title        | string   | Required                     |
| deadline     | datetime | Required                     |
| completed    | bool     | Default: False               |
| created_at   | datetime | Auto                         |
| updated_at   | datetime | Auto                         |

---

## API Endpoints

```
GET    /tasks
GET    /tasks/{id}
POST   /tasks
PUT    /tasks/{id}
DELETE /tasks/{id}
PATCH  /tasks/{id}/complete

GET    /projects
GET    /projects/{id}
POST   /projects
PUT    /projects/{id}
DELETE /projects/{id}
GET    /projects/{id}/tasks
POST   /projects/{project_id}/tasks/{task_id}/link
DELETE /projects/{project_id}/tasks/{task_id}/unlink
```

Filtering on `GET /tasks`: `?completed=`, `?overdue=`, `?project_id=`

---

## Business Rules (critical — enforced in the domain layer)

### Deadline Constraint
- A task's deadline **must never exceed** its project's deadline.
- Enforced in the domain model, not just at the API boundary.
- If a project's deadline is moved earlier and invalidates task deadlines → emit a `ProjectDeadlineUpdated` domain event → application layer handles it (adjust task deadlines or raise a graceful domain exception).

### Completion Lifecycle
- A project can only be marked complete if **all its tasks are completed**.
- Re-opening a completed task in a completed project → sets the **project back to open**.
- Config flag `AUTO_COMPLETE_PROJECT` (default: `False`): if `True`, automatically marks a project complete when its last open task is completed.

### Notifications / Logging (optional but recommended)
- Log when a task is marked completed.
- Log a warning if a task deadline is within 24 hours.
- Implemented as an in-memory event listener reacting to domain events.

---

## Domain Events
- `TaskCompleted`
- `TaskReopened`
- `ProjectDeadlineUpdated`
- `ProjectCompleted`

Events are raised by the domain, dispatched by the application service, and consumed by listeners (notification service, side-effect handlers).

---

## Configuration (`config.py`)
```python
AUTO_COMPLETE_PROJECT: bool = False  # auto-complete project when last task is done
```

---

## Persistence
- **SQLite** via SQLAlchemy (sync or async).
- Repositories implement abstract ports defined in `domain/ports/`.
- DB file stored at `/app/data/tasks.db` (volume-mounted in Docker).

---

## Testing
- Unit tests for domain models and business rules (no DB, no FastAPI).
- Integration tests for application services with a real SQLite in-memory DB.
- Use `pytest`.

---

## Key Constraints
- Business logic must have **zero** FastAPI or SQLAlchemy imports.
- Domain exceptions are caught and translated to HTTP errors at the API layer only.
- All IDs are UUIDs.
- Datetimes are UTC-aware.
