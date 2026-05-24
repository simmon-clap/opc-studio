"""Application configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

# backend/app/config.py -> project root is two levels up
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

DATA_DIR = Path(os.environ.get("OPC_DATA_DIR", str(PROJECT_ROOT / "data")))
DB_PATH = DATA_DIR / "opc.db"
MOCK_DASHBOARD_PATH = PROJECT_ROOT / "mock" / "dashboard.json"

HOST = os.environ.get("OPC_HOST", "127.0.0.1")
PORT = int(os.environ.get("OPC_PORT", "8765"))

_VERSION_FILE = PROJECT_ROOT / "VERSION"
if _VERSION_FILE.is_file():
    APP_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip()
else:
    APP_VERSION = "0.0.0-dev"

# Dev default; override in production via OPC_SECRET_KEY
SECRET_KEY = os.environ.get(
    "OPC_SECRET_KEY",
    "opc-dev-secret-key-change-in-production-32b!",
)

# Optional: Bridge → POST /channels/inbound 鉴权（留空则不校验）
CHANNEL_SECRET = os.environ.get("OPC_CHANNEL_SECRET", "")

# 公网暴露时 API Bearer 鉴权（留空则不校验）
ACCESS_TOKEN = os.environ.get("OPC_ACCESS_TOKEN", "")
