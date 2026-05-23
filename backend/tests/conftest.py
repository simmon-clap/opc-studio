"""Pytest fixtures."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import MOCK_DASHBOARD_PATH


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("OPC_DATA_DIR", str(data_dir))
    monkeypatch.setenv("OPC_PULSE_ENABLED", "0")
    monkeypatch.setattr("app.config.DATA_DIR", data_dir)
    monkeypatch.setattr("app.config.DB_PATH", data_dir / "opc.db")
    monkeypatch.setattr("app.db.DATA_DIR", data_dir)
    monkeypatch.setattr("app.db.DB_PATH", data_dir / "opc.db")

    import app.db as db_module
    import app.services.project_store as project_store

    db_module._engine = None
    monkeypatch.setattr(project_store, "DATA_DIR", data_dir)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    db_module._engine = None


GOLDEN_TOP_LEVEL_KEYS = {
    "meta",
    "pulse",
    "stats",
    "roles",
    "clients",
    "projects",
    "tasks",
    "hitlQueue",
    "alerts",
    "channels",
    "artifacts",
    "inbox",
    "rejectHistory",
    "closure",
    "payments",
    "weeklyReport",
    "rolePerformance",
    "ceoThread",
    "costs",
    "roleConfig",
    "commitments",
    "projectBriefs",
    "founderProfile",
    "profileSuggestions",
    "attachments",
    "dispatchFeed",
    "overviewLive",
    "presentation",
}


@pytest.fixture()
def golden_keys():
    with MOCK_DASHBOARD_PATH.open(encoding="utf-8") as fh:
        mock = json.load(fh)
    return set(mock.keys())
