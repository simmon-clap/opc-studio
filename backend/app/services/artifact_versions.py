"""Artifact versioning — snapshots and diffs."""

from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from typing import Any

from app.services.project_store import (
    read_artifact_file,
    read_artifact_version_file,
    write_artifact_version_file,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_version(version: str) -> tuple[int, int]:
    match = re.match(r"(\d+)\.(\d+)", version or "0.1")
    if not match:
        return 0, 1
    return int(match.group(1)), int(match.group(2))


def bump_version(current: str) -> str:
    major, minor = _parse_version(current)
    return f"{major}.{minor + 1}"


def append_version(
    art: dict[str, Any],
    content: str,
    *,
    author: str,
    note: str = "更新",
    project_id: str,
) -> str:
    """Snapshot content, bump art.version, return new version string."""
    current = art.get("version") or "0.1"
    versions: list[dict[str, Any]] = list(art.get("versions") or [])

    if not versions:
        versions.append(
            {
                "version": current,
                "at": art.get("updatedAt") or _now_iso(),
                "author": art.get("roleId") or author,
                "note": "初稿",
            }
        )
        write_artifact_version_file(project_id, art["id"], current, content)

    new_version = bump_version(current)
    versions.append(
        {
            "version": new_version,
            "at": _now_iso(),
            "author": author,
            "note": note,
        }
    )
    write_artifact_version_file(project_id, art["id"], new_version, content)

    art["version"] = new_version
    art["versions"] = versions[-20:]
    art["updatedAt"] = _now_iso()
    art["content"] = content
    return new_version


def init_version(
    art: dict[str, Any],
    content: str,
    *,
    author: str,
    project_id: str,
) -> None:
    version = art.get("version") or "0.1"
    art["versions"] = [
        {
            "version": version,
            "at": art.get("updatedAt") or _now_iso(),
            "author": author,
            "note": "初稿",
        }
    ]
    write_artifact_version_file(project_id, art["id"], version, content)


def get_version_content(project_id: str, artifact_id: str, version: str) -> str | None:
    stored = read_artifact_version_file(project_id, artifact_id, version)
    if stored is not None:
        return stored
    return read_artifact_file(project_id, artifact_id)


def diff_versions(
    project_id: str,
    artifact_id: str,
    from_version: str,
    to_version: str,
) -> dict[str, Any]:
    left = get_version_content(project_id, artifact_id, from_version) or ""
    right = get_version_content(project_id, artifact_id, to_version) or ""
    diff_lines = list(
        difflib.unified_diff(
            left.splitlines(),
            right.splitlines(),
            fromfile=f"v{from_version}",
            tofile=f"v{to_version}",
            lineterm="",
        )
    )
    return {
        "from": from_version,
        "to": to_version,
        "lines": diff_lines,
        "added": sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")),
        "removed": sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---")),
    }


def ensure_versions_meta(art: dict[str, Any], project_id: str) -> None:
    if art.get("versions"):
        return
    content = art.get("content") or read_artifact_file(project_id, art["id"]) or ""
    if content:
        init_version(art, content, author=art.get("roleId") or "system", project_id=project_id)
