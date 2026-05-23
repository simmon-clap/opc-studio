"""SQLite database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from app.config import DATA_DIR, DB_PATH
from app.models import (  # noqa: F401 — register all tables
    agent_runs,
    app_state,
    deliberation_sessions,
    deliberation_turns,
    handoffs,
    orchestration_events,
    role_secrets,
    schema_version,
    workflow_templates,
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
        )
        with _engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
            conn.commit()
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


@contextmanager
def session_scope():
    with Session(get_engine()) as session:
        yield session
