"""Role avatar upload storage."""

from __future__ import annotations

from pathlib import Path

from app.config import DATA_DIR

AVATAR_DIR = DATA_DIR / "uploads" / "avatars"
AVATAR_URL_PREFIX = "/assets/uploads/avatars"
MAX_BYTES = 5 * 1024 * 1024

MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP checked below
)


def _detect_mime(raw: bytes) -> str | None:
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    for sig, mime in _MAGIC:
        if sig == b"RIFF":
            continue
        if raw.startswith(sig):
            return mime
    return None


def save_role_avatar(role_id: str, raw: bytes, content_type: str | None) -> str:
    if len(raw) > MAX_BYTES:
        raise ValueError("FILE_TOO_LARGE")
    if not raw:
        raise ValueError("EMPTY_FILE")

    mime = _detect_mime(raw)
    if mime is None and content_type:
        mime = content_type.split(";")[0].strip().lower()
    if mime not in MIME_EXT:
        raise ValueError("UNSUPPORTED_FORMAT")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = MIME_EXT[mime]
    for old in AVATAR_DIR.glob(f"{role_id}.*"):
        if old.is_file():
            old.unlink()
    dest = AVATAR_DIR / f"{role_id}{ext}"
    dest.write_bytes(raw)
    return f"{AVATAR_URL_PREFIX}/{role_id}{ext}"


def resolve_avatar_url(role_id: str, stored: str | None = None) -> str:
    """Return a URL that matches an on-disk upload, else default avatar."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    if stored and stored.startswith(f"{AVATAR_URL_PREFIX}/"):
        name = Path(stored).name
        if (AVATAR_DIR / name).is_file():
            return stored
    for ext in MIME_EXT.values():
        path = AVATAR_DIR / f"{role_id}{ext}"
        if path.is_file():
            return f"{AVATAR_URL_PREFIX}/{role_id}{ext}"
    return f"/assets/avatars/{role_id}.png"
