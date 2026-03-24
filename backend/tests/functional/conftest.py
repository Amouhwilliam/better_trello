"""
Functional tests support two modes:

1. In-process (default) — TestClient wraps the ASGI app directly. No server
   needs to be running. DB is an isolated temp-file SQLite per module.

2. Live server — pass --api-url or set API_URL env var. httpx sends real HTTP
   requests to the running server. The server's own DB is used, so data from
   previous runs may be present (filter tests that assert on global state may
   see extra rows — that is expected and acceptable).

Usage:
    # in-process (default)
    pytest tests/functional/

    # against a running server
    API_URL=http://localhost:8000 pytest tests/functional/
    pytest tests/functional/ --api-url http://localhost:8000
"""

import os
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import infrastructure.db.orm_models  # noqa: F401 — registers ORM models with Base
from api.dependencies import get_current_user_id
from infrastructure.db.database import Base, get_db
from main import app

# Fixed UUID used as the authenticated user in all functional tests
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def pytest_addoption(parser):
    parser.addoption(
        "--api-url",
        action="store",
        default=None,
        help=(
            "Base URL of a running API server, e.g. http://localhost:8000. "
            "If omitted, tests run against the in-process ASGI app."
        ),
    )


@pytest.fixture(scope="module")
def client(request, tmp_path_factory):
    api_url = request.config.getoption("--api-url") or os.getenv("API_URL")

    if api_url:
        # ----------------------------------------------------------------
        # Live-server mode — httpx sends real HTTP requests to the server
        # ----------------------------------------------------------------
        with httpx.Client(base_url=api_url, timeout=10.0) as c:
            yield c

    else:
        # ----------------------------------------------------------------
        # In-process mode — TestClient runs the full ASGI app internally
        # ----------------------------------------------------------------
        db_path = tmp_path_factory.mktemp("functional_db") / "test.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine)

        def override_get_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

        # Patch init_db and _seed_default_user so the lifespan startup doesn't
        # try to write to /app/data/tasks.db (production path that doesn't exist locally).
        with patch("main.init_db"), patch("main._seed_default_user"), \
                TestClient(app, raise_server_exceptions=True) as c:
            yield c

        app.dependency_overrides.clear()
        engine.dispose()
