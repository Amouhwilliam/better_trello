"""
SQLite test database — follows the testcontainers interface pattern.

testcontainers is designed for server-based databases (Postgres, MySQL, etc.)
that need a Docker container to run. SQLite is an embedded, file-based database
and has no Docker image. The equivalent isolation strategy is a real temp file
per test (not in-memory), which gives the same guarantees:
  - isolated state between tests
  - real file I/O (not mocked)
  - automatic cleanup after the test

If this project were switched to Postgres, this fixture would be replaced with:
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16") as pg:
        engine = create_engine(pg.get_connection_url())
        ...
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import infrastructure.db.orm_models  # noqa: F401 — registers ORM models with Base
from infrastructure.db.database import Base


class SqliteTestDatabase:
    """
    Testcontainers-style context manager for an isolated, file-based SQLite DB.
    Uses pytest's tmp_path so the file is created fresh and cleaned up per test.
    """

    def __init__(self, tmp_path):
        self._db_path = tmp_path / "test.db"
        self._engine = None
        self._Session = None

    def __enter__(self):
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)
        return self

    def __exit__(self, *args):
        if self._engine:
            self._engine.dispose()

    def get_session(self):
        return self._Session()


@pytest.fixture
def db_session(tmp_path):
    """
    Yields a SQLAlchemy session backed by a real, isolated SQLite file.
    The database file is created fresh for each test and removed automatically
    by pytest when tmp_path is cleaned up.
    """
    with SqliteTestDatabase(tmp_path) as db:
        session = db.get_session()
        try:
            yield session
        finally:
            session.close()
