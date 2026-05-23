"""Deliverable kinds, templates, validation, and artifact building."""

from app.deliverables.artifact_builder import build_artifact_record, normalize_dashboard_artifacts
from app.deliverables.kinds import DeliverableSpec, resolve_deliverable
from app.deliverables.validator import validate_content

__all__ = [
    "DeliverableSpec",
    "build_artifact_record",
    "normalize_dashboard_artifacts",
    "resolve_deliverable",
    "validate_content",
]
