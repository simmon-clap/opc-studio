"""Project artifact file storage."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR


def project_dir(project_id: str) -> Path:
    return DATA_DIR / "projects" / project_id


def artifacts_dir(project_id: str) -> Path:
    return project_dir(project_id) / "artifacts"


def artifact_path(project_id: str, artifact_id: str) -> Path:
    return artifacts_dir(project_id) / f"{artifact_id}.md"


def deliveries_dir(project_id: str) -> Path:
    return project_dir(project_id) / "deliveries"


def ensure_project_dirs(project_id: str) -> None:
    artifacts_dir(project_id).mkdir(parents=True, exist_ok=True)
    deliveries_dir(project_id).mkdir(parents=True, exist_ok=True)


def write_artifact_file(project_id: str, artifact_id: str, content: str) -> str:
    ensure_project_dirs(project_id)
    path = artifact_path(project_id, artifact_id)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return hashlib.sha256(content.encode()).hexdigest()


def read_artifact_file(project_id: str, artifact_id: str) -> str | None:
    path = artifact_path(project_id, artifact_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def artifact_version_path(project_id: str, artifact_id: str, version: str) -> Path:
    safe = version.replace(".", "-")
    return artifacts_dir(project_id) / f"{artifact_id}.v{safe}.md"


def artifact_files_dir(project_id: str, artifact_id: str) -> Path:
    return artifacts_dir(project_id) / artifact_id / "files"


def write_artifact_version_file(
    project_id: str, artifact_id: str, version: str, content: str
) -> str:
    ensure_project_dirs(project_id)
    path = artifact_version_path(project_id, artifact_id, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def read_artifact_version_file(
    project_id: str, artifact_id: str, version: str
) -> str | None:
    path = artifact_version_path(project_id, artifact_id, version)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_artifact_files(
    project_id: str, artifact_id: str, files: list[dict[str, Any]]
) -> None:
    base = artifact_files_dir(project_id, artifact_id)
    for item in files:
        rel = (item.get("path") or "file.txt").lstrip("/")
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.get("content") or "", encoding="utf-8")


def read_artifact_files(project_id: str, artifact_id: str) -> list[dict[str, Any]]:
    base = artifact_files_dir(project_id, artifact_id)
    if not base.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(base))
            out.append({"path": rel, "content": path.read_text(encoding="utf-8")})
    return out


def sync_artifacts_from_dashboard(dashboard: dict[str, Any]) -> None:
    for art in dashboard.get("artifacts", []):
        project_id = art.get("projectId")
        artifact_id = art.get("id")
        content = art.get("content")
        if not project_id or not artifact_id or content is None:
            continue
        write_artifact_file(project_id, artifact_id, content)


def sync_artifact_to_dashboard(
    dashboard: dict[str, Any],
    project_id: str,
    artifact_id: str,
    content: str,
) -> dict[str, Any] | None:
    for art in dashboard.get("artifacts", []):
        if art.get("id") == artifact_id and art.get("projectId") == project_id:
            art["content"] = content
            art["updatedAt"] = datetime.now(timezone.utc).astimezone().isoformat(
                timespec="seconds"
            )
            return art
    return None


def get_artifact_meta(
    dashboard: dict[str, Any], project_id: str, artifact_id: str
) -> dict[str, Any] | None:
    for art in dashboard.get("artifacts", []):
        if art.get("id") == artifact_id and art.get("projectId") == project_id:
            return art
    return None
