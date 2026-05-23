"""OpenAI-compatible LLM client (OpenRouter, Moonshot, OpenAI, Ollama, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.services.role_config_service import RoleRuntimeConfig


@dataclass
class LlmResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    raw: dict[str, Any]


class LlmError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _is_moonshot_config(config: RoleRuntimeConfig) -> bool:
    base = (config.api_base_url or "").lower()
    model = (config.model or "").lower()
    provider = (config.api_provider or "").lower()
    return (
        provider == "moonshot"
        or "moonshot.cn" in base
        or "moonshot" in base
        or "kimi" in model
        or model.startswith("moonshot")
    )


def _temperature_for_payload(config: RoleRuntimeConfig, requested: float) -> int | float:
    """Moonshot / Kimi 仅允许 temperature=1（整数）。"""
    if _is_moonshot_config(config):
        return 1
    return requested


async def chat_completion(
    config: RoleRuntimeConfig,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 2048,
    temperature: float = 0.4,
) -> LlmResponse:
    if not config.is_configured:
        raise LlmError("LLM_NOT_CONFIGURED", f"{config.role_id} 未配置 API Key 或 Base URL")

    resolved_temp = _temperature_for_payload(config, temperature)

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if config.api_provider == "OpenRouter":
        headers["HTTP-Referer"] = "http://127.0.0.1:8765"
        headers["X-Title"] = "OPC Studio"

    payload = {
        "model": config.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": resolved_temp,
    }

    url = _chat_url(config.api_base_url)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            # 部分模型报错时自动重试 temperature=1
            if resp.status_code == 400 and "temperature" in resp.text.lower():
                payload["temperature"] = 1
                resp = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise LlmError("LLM_TIMEOUT", "请求超时，请检查网络或 Base URL") from exc
    except httpx.RequestError as exc:
        raise LlmError("LLM_NETWORK", f"网络错误：{exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text[:500]
        raise LlmError(
            "LLM_HTTP_ERROR",
            f"HTTP {resp.status_code}: {detail}",
            status=resp.status_code,
        )

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise LlmError("LLM_EMPTY", "模型返回为空")

    content = choices[0].get("message", {}).get("content") or ""
    usage = data.get("usage") or {}
    return LlmResponse(
        content=content.strip(),
        model=data.get("model") or config.model,
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
        raw=data,
    )


async def test_connection(config: RoleRuntimeConfig) -> LlmResponse:
    return await chat_completion(
        config,
        [
            {
                "role": "user",
                "content": "Reply with exactly: OPC_OK",
            }
        ],
        max_tokens=16,
        temperature=1 if _is_moonshot_config(config) else 0,
    )


def estimate_cost_cny(input_tokens: int, output_tokens: int) -> float:
    # 粗算：约 ¥0.01 / 1k tokens，后续可按模型表细化
    return round((input_tokens + output_tokens) * 0.01 / 1000, 2)
