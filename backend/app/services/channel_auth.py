"""Optional shared secret for channel ingress (Bridge → OPC)."""

from __future__ import annotations

from fastapi import Header

from app.config import CHANNEL_SECRET


def verify_channel_token(
    authorization: str | None = Header(default=None),
    x_opc_channel_token: str | None = Header(default=None, alias="X-OPC-Channel-Token"),
) -> None:
    """Raise ValueError('UNAUTHORIZED') when secret configured and token mismatch."""
    secret = (CHANNEL_SECRET or "").strip()
    if not secret:
        return
    token = (x_opc_channel_token or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if token != secret:
        raise ValueError("UNAUTHORIZED")
