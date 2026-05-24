"""Image / video generation via OpenAI-compatible APIs."""

from __future__ import annotations

from typing import Any

import httpx

from app.services.llm_client import LlmError
from app.services.role_config_service import get_role_runtime_config


def _api_base(config) -> str:
    base = (config.api_base_url or "").rstrip("/")
    if base.endswith("/chat/completions"):
        base = base.rsplit("/", 2)[0]
    return base


def _auth_headers(config) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }


async def generate_image(
    session,
    dashboard: dict[str, Any],
    role_id: str,
    prompt: str,
    *,
    capability: str = "image",
) -> dict[str, Any]:
    return await generate_media(
        session, dashboard, role_id, prompt, capability=capability
    )


async def generate_video(
    session,
    dashboard: dict[str, Any],
    role_id: str,
    prompt: str,
) -> dict[str, Any]:
    return await generate_media(
        session, dashboard, role_id, prompt, capability="video"
    )


async def generate_media(
    session,
    dashboard: dict[str, Any],
    role_id: str,
    prompt: str,
    *,
    capability: str = "image",
) -> dict[str, Any]:
    config = get_role_runtime_config(session, dashboard, role_id, capability=capability)
    if not config.is_configured:
        raise LlmError("MEDIA_NOT_CONFIGURED", f"{role_id} 未配置 {capability} 模型 Key")

    base = _api_base(config)
    headers = _auth_headers(config)
    path = "/videos/generations" if capability == "video" else "/images/generations"
    url = f"{base}{path}"
    payload: dict[str, Any] = {
        "model": config.model or ("sora" if capability == "video" else "dall-e-3"),
        "prompt": prompt[:2000],
        "n": 1,
    }
    if capability == "image":
        payload["size"] = "1024x1024"
    else:
        payload["duration"] = 5

    async with httpx.AsyncClient(timeout=180.0) as client:
        res = await client.post(url, json=payload, headers=headers)

    if res.status_code == 404 and capability == "video":
        return {
            "ok": True,
            "type": "video",
            "url": None,
            "placeholder": True,
            "caption": prompt[:120],
            "model": config.model,
            "detail": "Provider 无 /videos/generations，返回占位元数据",
        }

    if res.status_code >= 400:
        raise LlmError("MEDIA_HTTP_ERROR", res.text[:300], status=res.status_code)

    data = res.json()
    item = (data.get("data") or [{}])[0]
    url_out = item.get("url") or item.get("b64_json") or item.get("video_url")
    return {
        "ok": True,
        "type": capability,
        "url": url_out if isinstance(url_out, str) and url_out.startswith("http") else None,
        "b64": url_out if url_out and not str(url_out).startswith("http") else None,
        "caption": prompt[:120],
        "model": config.model,
    }
