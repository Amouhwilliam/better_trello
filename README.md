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
├── api/          # FastAPI backend
├── frontend/     # Next.js frontend
└── docker-compose.yml
```

## Running the App

### Start everything at once

```bash
docker compose up --build
```

| Service  | URL                       |
|----------|---------------------------|
| Frontend | http://localhost:3000     |
| API      | http://localhost:8000     |
| API Docs | http://localhost:8000/docs |

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
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```
