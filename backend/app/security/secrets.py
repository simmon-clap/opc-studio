"""Fernet encryption helpers for API keys."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import SECRET_KEY


def _fernet() -> Fernet:
    digest = hashlib.sha256(SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def mask_api_key(api_key: str | None) -> dict | None:
    if not api_key:
        return None
    if len(api_key) <= 4:
        return {"masked": "****"}
    return {"masked": f"{'*' * (len(api_key) - 4)}{api_key[-4:]}"}
