# Better Trello

A full-stack project management app inspired by Trello.

## Stack

| Layer    | Technology                        |
|----------|-----------------------------------|
| Frontend | Next.js 15, TypeScript, Tailwind  |
| Backend  | FastAPI, Python 3.12              |
| Runtime  | Docker, Docker Compose            |

## Project Structure

```
better_trello/
├── backend/      # FastAPI backend
├── frontend/     # Next.js frontend
└── docker-compose.yml
```

## Running the App

### Start everything at once

```bash
docker compose up --build
```

| Service       | URL                        |
|---------------|----------------------------|
| Frontend      | http://localhost:3000      |
| API           | http://localhost:8000      |
| API Docs      | http://localhost:8000/docs |
| Datasette (DB)| http://localhost:8081      |

### Stop all services

```bash
docker compose down
```

### Rebuild after dependency changes

```bash
docker compose up --build
```

## Development

### API (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

## Testing

Unit tests cover all domain models and business rules with no framework dependencies (no FastAPI, no database).

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

### Run the tests

```bash
cd backend
.venv/bin/python -m pytest tests/ -v
```

Or activate the venv first:

```bash
source backend/.venv/bin/activate
cd backend && pytest tests/ -v
```

### Test structure

```
backend/tests/
├── conftest.py          # shared fixtures (Task, Project, date helpers)
└── unit/domain/
    ├── test_task.py     # 30 tests — Task creation, update, assignment,
    │                    #   completion, reopen, overdue, events
    └── test_project.py  # 26 tests — Project creation, update, deadline events,
                         #   completion lifecycle, auto-complete flag
```

### What's tested

| Area | Tests |
|---|---|
| Task defaults & UUID generation | `TestTaskCreation` |
| Task field updates & deadline validation | `TestTaskUpdate` |
| Task ↔ Project association / unlinking | `TestTaskProjectAssociation` |
| `mark_complete` / `reopen` lifecycle & events | `TestTaskCompletion`, `TestTaskReopen` |
| Force deadline adjustment (`adjust_deadline`) | `TestTaskAdjustDeadline` |
| Overdue detection | `TestTaskOverdue` |
| Event queue (`pull_events`) | `TestTaskPullEvents` |
| Project defaults & UUID generation | `TestProjectCreation` |
| Project title / deadline updates | `TestProjectUpdate` |
| `ProjectDeadlineUpdated` event on earlier deadline | `TestProjectUpdate` |
| `mark_complete` guards (all tasks must be done) | `TestProjectCompletion` |
| Project reopen | `TestProjectReopen` |
| `AUTO_COMPLETE_PROJECT` flag behaviour | `TestProjectAutoComplete` |
| Event queue (`pull_events`) | `TestProjectPullEvents` |
