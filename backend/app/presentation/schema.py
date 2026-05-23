"""Presentation layer schema version and block type constants."""

from __future__ import annotations

PRESENTATION_VERSION = 1

# Block types consumed by dashboards/app/js/presentation.js
BLOCK_PARAGRAPH = "paragraph"
BLOCK_HEADING = "heading"
BLOCK_LIST = "list"
BLOCK_CALLOUT = "callout"
BLOCK_TASK_ROW = "task_row"

# Overview dialogue tones
TONE_ASSIGN = "assign"
TONE_REPLY = "reply"
TONE_DELIVER = "deliver"
TONE_FAIL = "fail"

# Overview anchor modes
ANCHOR_EDGE = "edge"
ANCHOR_ROLE = "role"
