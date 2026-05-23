"""Versioned presentation layer — derived views for dashboard UI.

Architecture
------------
- **Source of truth**: tasks, dispatchFeed (events), ceoThread (messages)
- **Derived views**: ``dashboard["presentation"]`` rebuilt on every ``recompute_all``
- **UI contract**: frontends read ``presentation.*``; top-level aliases kept for compat

Extend by adding a computer in ``derived.py`` and a block builder in ``blocks.py``.
"""

from app.presentation.derived import recompute_presentation
from app.presentation.schema import PRESENTATION_VERSION

__all__ = ["PRESENTATION_VERSION", "recompute_presentation"]
