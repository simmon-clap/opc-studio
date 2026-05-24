"""Per-capability API credentials stored on RoleSecret."""

from __future__ import annotations

import json
from typing import Any

from app.models.role_secrets import RoleSecret
from app.security.secrets import decrypt, encrypt

SLOT_KEYS = ("text", "image", "video", "code")


def _empty_slots() -> dict[str, dict[str, Any]]:
    return {cap: {"api_base_url": None, "api_key_encrypted": None} for cap in SLOT_KEYS}


def load_slot_store(row: RoleSecret | None) -> dict[str, dict[str, Any]]:
    if row is None:
        return _empty_slots()
    if row.slot_credentials_json:
        try:
            raw = json.loads(row.slot_credentials_json)
            if isinstance(raw, dict):
                store = _empty_slots()
                for cap in SLOT_KEYS:
                    slot = raw.get(cap) if isinstance(raw.get(cap), dict) else {}
                    store[cap] = {
                        "api_base_url": slot.get("api_base_url"),
                        "api_key_encrypted": slot.get("api_key_encrypted"),
                    }
                return store
        except json.JSONDecodeError:
            pass
    # Legacy single-row credentials → text slot
    store = _empty_slots()
    if row.api_base_url or row.api_key_encrypted:
        store["text"] = {
            "api_base_url": row.api_base_url,
            "api_key_encrypted": row.api_key_encrypted,
        }
    return store


def save_slot_store(row: RoleSecret, store: dict[str, dict[str, Any]]) -> None:
    row.slot_credentials_json = json.dumps(store, ensure_ascii=False)
    text = store.get("text") or {}
    row.api_base_url = text.get("api_base_url")
    row.api_key_encrypted = text.get("api_key_encrypted")


def get_slot_runtime(row: RoleSecret | None, capability: str) -> dict[str, Any]:
    cap = capability if capability in SLOT_KEYS else "text"
    store = load_slot_store(row)
    slot = store.get(cap) or {}
    api_key = None
    enc = slot.get("api_key_encrypted")
    if enc:
        try:
            api_key = decrypt(enc)
        except Exception:
            api_key = None
    return {
        "api_base_url": slot.get("api_base_url"),
        "api_key": api_key,
        "api_key_configured": bool(api_key),
    }


def patch_slot(
    row: RoleSecret,
    capability: str,
    *,
    api_base_url: str | None = None,
    api_key: str | None = None,
) -> None:
    cap = capability if capability in SLOT_KEYS else "text"
    store = load_slot_store(row)
    slot = store.setdefault(cap, {"api_base_url": None, "api_key_encrypted": None})
    if api_base_url is not None:
        slot["api_base_url"] = api_base_url.rstrip("/") if api_base_url else None
    if api_key:
        slot["api_key_encrypted"] = encrypt(api_key)
    save_slot_store(row, store)


def slot_configured(row: RoleSecret | None, capability: str) -> bool:
    rt = get_slot_runtime(row, capability)
    return bool(rt["api_key"] and rt["api_base_url"])
