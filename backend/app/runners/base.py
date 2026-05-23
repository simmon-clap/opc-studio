"""Role runner base (Phase 3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RunContext:
    def __init__(self, dashboard: dict[str, Any], project_id: str, task: dict[str, Any]):
        self.dashboard = dashboard
        self.project_id = project_id
        self.task = task


class RunResult:
    def __init__(
        self,
        *,
        artifact_id: str | None = None,
        artifact_content: str | None = None,
        artifact_title: str | None = None,
        artifact_type: str = "doc",
        artifact_kind: str | None = None,
        artifact_format: str = "markdown",
        artifact_viewer: str | None = None,
        artifact_group: str | None = None,
        template_id: str | None = None,
        artifact_status: str = "draft",
        artifact_quality: dict | None = None,
        artifact_files: list[dict] | None = None,
        artifact_images: list[dict] | None = None,
        demo_url: str | None = None,
        handoff_to: str = "ceo",
        progress_note: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str = "stub",
        cost_cny: float = 0.0,
    ):
        self.artifact_id = artifact_id
        self.artifact_content = artifact_content
        self.artifact_title = artifact_title
        self.artifact_type = artifact_type
        self.artifact_kind = artifact_kind
        self.artifact_format = artifact_format
        self.artifact_viewer = artifact_viewer
        self.artifact_group = artifact_group
        self.template_id = template_id
        self.artifact_status = artifact_status
        self.artifact_quality = artifact_quality or {}
        self.artifact_files = artifact_files or []
        self.artifact_images = artifact_images or []
        self.demo_url = demo_url
        self.handoff_to = handoff_to
        self.progress_note = progress_note
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.model = model
        self.cost_cny = cost_cny


class RoleRunner(ABC):
    role_id: str

    @abstractmethod
    async def run(self, ctx: RunContext) -> RunResult:
        ...
