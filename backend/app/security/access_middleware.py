"""Optional Bearer token gate for API (OPC_ACCESS_TOKEN)."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import ACCESS_TOKEN

_PUBLIC_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/dashboards/",
    "/assets/",
    "/architecture.html",
    "/favicon.ico",
)


def _is_public(path: str) -> bool:
    if path in ("/", "/api/v1/health"):
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


class AccessTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = (ACCESS_TOKEN or "").strip()
        if not token or _is_public(request.url.path):
            return await call_next(request)
        auth = request.headers.get("authorization") or ""
        query = request.query_params.get("access_token") or ""
        bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if bearer == token or query == token:
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "缺少或无效的 OPC_ACCESS_TOKEN",
                    "details": {},
                },
            },
        )
