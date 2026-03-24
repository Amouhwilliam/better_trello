# Design & Architecture

This document describes the architectural decisions, patterns, and layer responsibilities for both the backend and frontend of Better Trello.

---

## Table of Contents

1. [Backend — Hexagonal Architecture](#backend--hexagonal-architecture)
   - [Layer Overview](#layer-overview)
   - [Domain Layer](#domain-layer)
   - [Application Layer](#application-layer)
   - [Infrastructure Layer](#infrastructure-layer)
   - [API Layer](#api-layer)
   - [Domain Events](#domain-events)
   - [Business Rules](#business-rules)
   - [Authentication](#authentication)
   - [Notifications](#notifications)
   - [Testing Strategy](#testing-strategy)
2. [Frontend — Next.js App Router](#frontend--nextjs-app-router)
   - [Rendering Model](#rendering-model)
   - [State Management](#state-management)
   - [API Client](#api-client)
   - [Auth Flow](#auth-flow)
   - [Page & Component Structure](#page--component-structure)
   - [UI Patterns](#ui-patterns)

---

## Backend — Hexagonal Architecture

The backend is built with **Hexagonal Architecture** (also called Ports & Adapters). The core idea is that business logic is completely isolated from frameworks, databases, and I/O. FastAPI and SQLAlchemy are treated as external details that plug into the core — not the other way around.

### Layer Overview

```
┌─────────────────────────────────────────────────────────┐
│                        API Layer                        │  ← FastAPI routers, Pydantic schemas,
│               (api/routers/, api/schemas/)              │    dependency injection
└────────────────────────────┬────────────────────────────┘
                             │ calls
┌────────────────────────────▼────────────────────────────┐
│                   Application Layer                     │  ← Use-case services, orchestration,
│           (application/task_service.py, ...)            │    event dispatch
└───────────┬────────────────────────────────┬────────────┘
            │ uses ports                     │ uses ports
┌───────────▼──────────┐       ┌─────────────▼────────────┐
│    Domain Layer      │       │   Infrastructure Layer   │  ← SQLAlchemy repositories,
│  (domain/)           │       │   (infrastructure/)      │    notification adapters
│  Pure Python         │       │   Implements the ports   │
│  No framework deps   │       └──────────────────────────┘
└──────────────────────┘
```

### Domain Layer

**Path:** `backend/domain/`

The domain is the heart of the application. It contains zero imports from FastAPI, SQLAlchemy, or any I/O library.

```
domain/
├── models/
│   ├── task.py       # Task entity with all business rules
│   ├── project.py    # Project entity with completion lifecycle
│   └── user.py       # User entity
├── events/
│   └── __init__.py   # Domain event dataclasses
├── exceptions/
│   └── __init__.py   # Domain-specific exceptions
└── ports/
    ├── repositories.py        # Abstract repository interfaces
    └── notification_port.py   # Abstract notification interface
```

**Entities** are plain Python dataclasses that enforce business rules in their methods:

- `Task.assign_to_project(project_id, project_deadline)` — raises `DeadlineConstraintError` if the task deadline exceeds the project deadline.
- `Task.mark_complete()` — sets `completed = True` and emits a `TaskCompleted` event.
- `Task.reopen()` — sets `completed = False` and emits a `TaskReopened` event.
- `Project.mark_complete(tasks)` — raises `ProjectCompletionError` if any task is still open.
- `Project.try_auto_complete(tasks)` — auto-completes the project only if `auto_complete=True` and all tasks are done.
- `Project.update(deadline, tasks)` — emits `ProjectDeadlineUpdated` if the new deadline is earlier and some tasks would violate it.

**Ports** are abstract base classes (Python `ABC`) that define what the application layer needs — repositories and notification services. The infrastructure layer provides concrete implementations.

```python
# Example port — the domain defines the interface, infrastructure implements it
class TaskRepository(ABC):
    @abstractmethod
    def find_by_id(self, task_id: UUID) -> Optional[Task]: ...
    @abstractmethod
    def save(self, task: Task) -> Task: ...
    @abstractmethod
    def delete(self, task_id: UUID) -> None: ...
```

### Application Layer

**Path:** `backend/application/`

Application services are the use-case orchestrators. They:

1. Load entities through repository ports.
2. Call domain methods that enforce business rules.
3. Persist changes through repository ports.
4. Pull domain events and dispatch them to the notification port.
5. Handle cross-aggregate side effects (e.g., reopening a completed project when a task is reopened).

```
application/
├── task_service.py     # CRUD + complete/reopen + assign + link/unlink
├── project_service.py  # CRUD + complete + deadline clamping
└── user_service.py     # CRUD
```

The services have **no knowledge of HTTP**. They raise domain exceptions (`TaskNotFoundError`, `DeadlineConstraintError`, etc.) which the API layer translates into HTTP responses.

**Example flow — completing a task:**

```
POST /tasks/{id}/complete
  → TaskService.complete_task(task_id)
      → task_repo.find_by_id(task_id)
      → task.mark_complete()              # domain rule, emits TaskCompleted event
      → task_repo.save(task)
      → notifications.dispatch_all(events)
      → _try_auto_complete_project(task.project_id)  # side-effect
```

### Infrastructure Layer

**Path:** `backend/infrastructure/`

Concrete adapters that implement the domain ports.

```
infrastructure/
├── db/
│   ├── orm_models.py              # SQLAlchemy ORM models (separate from domain)
│   ├── database.py                # Engine setup, get_db session factory
│   ├── task_repository.py         # SQLiteTaskRepository implements TaskRepository
│   ├── project_repository.py      # SQLiteProjectRepository implements ProjectRepository
│   └── user_repository.py         # SQLiteUserRepository implements UserRepository
└── notifications/
    ├── notification_service.py         # Console logger (implements NotificationPort)
    ├── file_notification_service.py    # File logger (implements NotificationPort)
    └── composite_notification_service.py  # Combines multiple services (Composite pattern)
```

**ORM ↔ Domain mapping:** The ORM models are intentionally separate from the domain models. Each repository maps between them in `to_domain()` and `from_domain()` methods. This means the domain is never polluted with SQLAlchemy column definitions or session management.

**UTC handling:** SQLite stores datetimes as naive strings. All datetimes are stored as UTC and `.replace(tzinfo=timezone.utc)` is applied on read to restore timezone-awareness.

**Composite Notification:** The app uses a `CompositeNotificationService` that fans out to both a console logger and a file logger. Adding a new notification channel (e.g. email, Slack) requires only writing a new adapter implementing `NotificationPort` — no changes to the application or domain.

### API Layer

**Path:** `backend/api/`

```
api/
├── routers/
│   ├── auth.py       # POST /auth/login
│   ├── tasks.py      # Full CRUD + status, assign, complete
│   ├── projects.py   # Full CRUD + complete, link/unlink tasks
│   └── users.py      # Full CRUD + GET /users/me
├── schemas/
│   ├── task.py       # TaskCreate, TaskUpdate, TaskResponse (Pydantic v2)
│   ├── project.py    # ProjectCreate, ProjectUpdate, ProjectResponse
│   └── user.py       # UserCreate, UserUpdate, UserResponse
├── dependencies.py   # get_db, get_*_service, get_current_user_id (JWT)
└── exception_handlers.py  # Maps domain exceptions → HTTP status codes
```

Domain exceptions are caught once in `exception_handlers.py` and translated to appropriate HTTP responses:

| Domain Exception           | HTTP Status |
|----------------------------|-------------|
| `TaskNotFoundError`        | 404         |
| `ProjectNotFoundError`     | 404         |
| `UserNotFoundError`        | 404         |
| `DeadlineConstraintError`  | 422         |
| `ProjectCompletionError`   | 422         |
| `UserAlreadyExistsError`   | 409         |

### Domain Events

Events are raised inside domain methods and collected in an internal `_pending_events` list. The application service calls `entity.pull_events()` after saving to drain and dispatch them.

| Event                    | Raised by                         | Consumed by                                 |
|--------------------------|-----------------------------------|---------------------------------------------|
| `TaskCompleted`          | `Task.mark_complete()`            | `NotificationService` (logs completion)     |
| `TaskReopened`           | `Task.reopen()`                   | `TaskService` (reopens parent project)      |
| `ProjectCompleted`       | `Project.mark_complete()`, `try_auto_complete()` | `NotificationService`          |
| `ProjectDeadlineUpdated` | `Project.update(deadline, tasks)` | `ProjectService` (clamps task deadlines)    |

Events decouple side effects from the core action. The application service decides what to do with an event — the domain only records that something happened.

### Business Rules

All rules are enforced in the **domain layer**, never just at the API boundary:

- **Deadline constraint:** A task's deadline must never exceed its parent project's deadline. Enforced in `Task.assign_to_project()` and `Task.update()`.
- **Project completion guard:** A project can only be marked complete when all its tasks are done. Enforced in `Project.mark_complete(tasks)`.
- **Auto-complete:** A per-project flag (`auto_complete`). When the last open task in a project is completed, `Project.try_auto_complete(tasks)` is called — it completes the project automatically if the flag is on.
- **Reopen cascade:** Re-opening a completed task in a completed project sets the project back to open. The `TaskReopened` event carries the `project_id` for the service to act on.
- **Deadline clamping:** When a project's deadline moves earlier, any tasks whose deadline would now exceed it are automatically adjusted via the `ProjectDeadlineUpdated` event.

### Authentication

JWT-based authentication using **PyJWT**.

- `POST /auth/login` validates email + bcrypt password, returns a signed JWT.
- The token payload contains `sub` = user UUID and `exp` = expiry timestamp.
- All protected endpoints depend on `get_current_user_id` which decodes the Bearer token and returns the UUID.
- The frontend stores the token in an HTTP-only cookie (`bt_token`).

### Notifications

The notification system follows the **Adapter pattern**:

```
NotificationPort (abstract)
  ├── NotificationService       → logs to console (stdout)
  ├── FileNotificationService   → appends to a log file
  └── CompositeNotificationService → fans out to N adapters
```

Triggered events:
- Task completed → log title + timestamp.
- Task deadline within 24 hours → log a warning.
- Project completed → log title + timestamp.
- Project deadline moved earlier → log affected task count.

### Testing Strategy

Tests are organized in three layers mirroring the architecture:

| Layer | Scope | DB | HTTP |
|---|---|---|---|
| **Unit** | Domain models, notification adapters | No | No |
| **Integration** | Application services + repositories | Real SQLite (temp file) | No |
| **Functional** | Full HTTP stack end-to-end | Real SQLite (temp file) | Yes (TestClient or live server) |

The functional test suite supports two modes:
- **In-process** (default): `TestClient` wraps the ASGI app. Fast, isolated, no server needed.
- **Live server**: `API_URL=http://localhost:8000 pytest tests/functional/` sends real HTTP requests to a running instance.

---

## Frontend — Next.js App Router

### Rendering Model

The app uses **Next.js 15 App Router** with a clear split between server and client components:

| Component type | Used for | Example |
|---|---|---|
| **Server Component** | Auth guard (reads cookies), initial redirect, static shell | `dashboard/page.tsx`, `projects/[id]/page.tsx` |
| **Client Component** | All interactive UI, data fetching, mutations | `DashboardClient.tsx`, `BoardClient.tsx` |

Server components handle the authentication check (read the `bt_token` cookie, redirect to `/` if absent) and then render the client component shell. All data fetching happens on the client via React Query — there is no server-side data fetching beyond the auth check.

### State Management

**TanStack Query (React Query)** is the primary state layer. It handles:

- Fetching, caching, background refetching, and invalidation.
- Optimistic updates on drag-and-drop task status changes.
- Global user state via `queryKey: ["me"]` — the current user is fetched once and shared across the app without a separate store or context.

Key query keys:

| Key | Data | Stale strategy |
|---|---|---|
| `["me"]` | Authenticated user | Default (re-fetched on focus) |
| `["projects"]` | All projects | Default |
| `["project-tasks", projectId]` | Tasks for a board | `refetchOnMount: "always"` |
| `["users"]` | All users | Default |
| `["all-tasks"]` | All platform tasks | Default |

`refetchOnMount: "always"` on `project-tasks` ensures the board always shows fresh data when navigating to a project, even if the cache is warm.

### API Client

**Path:** `frontend/lib/api.ts`

A single typed module that wraps all backend calls. It:

- Reads the JWT from the `bt_token` cookie on every request.
- Attaches the `Authorization: Bearer <token>` header automatically.
- Intercepts 401 responses to clear the cookie and redirect to login.
- Throws `Error` with the API's `detail` message on non-OK responses (React Query surfaces this to `onError` handlers).

```typescript
export const api = {
  users: { me, list, get, create },
  projects: { list, get, create, update, complete, tasks },
  tasks: { list, create, update, updateStatus, assign, unassign, linkProject, unlinkProject },
}
```

All methods are strongly typed with exported interfaces (`User`, `Project`, `Task`, `TaskStatus`).

### Auth Flow

```
User visits /dashboard
  → Server component reads bt_token cookie
  → Not found → redirect("/")
  → Found → render <DashboardClient />
      → useQuery(["me"]) → GET /users/me
      → Renders greeting + avatar from response
```

Login:
```
POST /api/auth/login (Next.js API route)
  → Proxies to backend POST /auth/login
  → Sets bt_token as HTTP-only cookie
  → Redirects to /dashboard
```

Logout:
```
POST /api/auth/logout (Next.js API route)
  → Clears bt_token cookie
  → Redirects to /
```

The userId is **never stored in the URL**. The `["me"]` query acts as the single source of truth for the current user's identity.

### Page & Component Structure

```
app/
├── page.tsx                        # Login page (public)
├── register/page.tsx               # Register page (public)
├── dashboard/
│   ├── page.tsx                    # Server: auth guard → renders DashboardClient
│   ├── DashboardClient.tsx         # Client: tabs (Projects / Contributors / Tasks)
│   └── SignOutButton.tsx           # Client: logout action
├── projects/[id]/
│   ├── page.tsx                    # Server: auth guard, fetches project metadata
│   └── BoardClient.tsx             # Client: Kanban board with drag-and-drop
└── api/
    ├── auth/login/route.ts         # Next.js API route: proxies login, sets cookie
    ├── auth/logout/route.ts        # Next.js API route: clears cookie
    └── users/lookup/route.ts       # Next.js API route: server-side user lookup
```

### UI Patterns

**Tabs (Dashboard):** Three tabs — Projects, Contributors, Tasks — implemented with local `useState`. Each tab lazily enables its query (`enabled: tab === "tasks"`).

**Kanban Board:** Uses `@hello-pangea/dnd` for drag-and-drop. Status changes trigger an optimistic update (instant UI) followed by a `PATCH /tasks/{id}/status` mutation. On error, the cache rolls back to the previous state.

**Pagination (Tasks tab):** Client-side, 15 items per page. Page state resets when switching tabs. Shows "Showing X–Y of Z" summary and numbered page buttons.

**Modals:** All modals follow the same pattern — rendered conditionally from parent state, backdrop click to close, `react-hook-form` + `zod` for validation, `useMutation` for the action, `toast` (Sonner) for feedback.

**Inline edit (Project cell in Tasks table):** The project cell in the Tasks table shows a pencil icon on hover. Clicking it opens `TaskProjectModal` which allows searching all projects and linking/unlinking one via the backend endpoints.

**Forms:** All forms use `react-hook-form` with `zod` schema resolvers. Errors are rendered inline. The submit button is disabled while the mutation is pending.
