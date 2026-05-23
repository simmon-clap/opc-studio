"""Role configuration endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.security.secrets import encrypt, mask_api_key
from app.services.dashboard_store import get_dashboard, mutate
from app.services.llm_client import LlmError, test_connection
from app.runners.prompts import default_role_prompt
from app.services.role_config_service import get_role_runtime_config
from app.models.role_secrets import RoleSecret

router = APIRouter(tags=["roles"])


class RoleConfigUpdate(BaseModel):
    model: str | None = None
    apiProvider: str | None = None
    apiBaseUrl: str | None = None
    apiKey: str | None = None
    monthlyBudget: int | None = None
    tools: list[str] | None = None
    rolePrompt: str | None = None


class RoleConfigTestBody(BaseModel):
    """测试连接时可传入表单当前值（不必先落库）。"""
    model: str | None = None
    apiProvider: str | None = None
    apiBaseUrl: str | None = None
    apiKey: str | None = None


def _merge_test_runtime(
    runtime: RoleRuntimeConfig, body: RoleConfigTestBody | None
) -> RoleRuntimeConfig:
    if body is None:
        return runtime
    from dataclasses import replace

    return replace(
        runtime,
        model=body.model or runtime.model,
        api_provider=body.apiProvider or runtime.api_provider,
        api_base_url=(body.apiBaseUrl or runtime.api_base_url).rstrip("/"),
        api_key=body.apiKey or runtime.api_key,
    )


def _build_role_config(session: Session, dashboard: dict) -> list[dict]:
    configs = []
    for cfg in dashboard.get("roleConfig", []):
        role_id = cfg.get("roleId")
        row = session.get(RoleSecret, role_id) if role_id else None
        role = next(
            (r for r in dashboard.get("roles", []) if r.get("id") == role_id),
            {},
        )
        item = dict(cfg)
        if not (item.get("rolePrompt") or "").strip():
            item["rolePrompt"] = default_role_prompt(
                role_id or "",
                role.get("name") or role_id or "",
                role.get("charter") or "",
            )
        if row and row.api_base_url:
            item["apiBaseUrl"] = row.api_base_url
        if row and row.api_key_encrypted:
            from app.security.secrets import decrypt

            item["apiKey"] = mask_api_key(decrypt(row.api_key_encrypted))
        else:
            item["apiKey"] = None
        configs.append(item)
    return configs


@router.get("/roles")
def list_roles(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(dashboard.get("roles", []))


@router.get("/roles/{role_id}/tasks")
def role_tasks(role_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    tasks = [t for t in dashboard.get("tasks", []) if t.get("roleId") == role_id]
    running = [t for t in tasks if t.get("status") == "running"]
    pending = [t for t in tasks if t.get("status") == "pending"]
    return ok({"running": running, "pending": pending})


@router.get("/roles/config")
def get_roles_config(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(_build_role_config(session, dashboard))


@router.put("/roles/config/{role_id}")
def update_role_config(
    role_id: str,
    body: RoleConfigUpdate,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        None,
    )
    if cfg is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)

    updates = body.model_dump(exclude_none=True)
    api_key = updates.pop("apiKey", None)

    with mutate(session) as dash:
        target = next(c for c in dash["roleConfig"] if c.get("roleId") == role_id)
        for key, value in updates.items():
            target[key] = value

    row = session.get(RoleSecret, role_id)
    now = datetime.now(timezone.utc)
    if row is None:
        row = RoleSecret(role_id=role_id, updated_at=now)
    if body.apiBaseUrl is not None:
        row.api_base_url = body.apiBaseUrl
    if api_key:
        row.api_key_encrypted = encrypt(api_key)
    row.updated_at = now
    session.add(row)
    session.commit()

    dashboard = get_dashboard(session)
    updated = next(c for c in _build_role_config(session, dashboard) if c["roleId"] == role_id)
    return ok(updated)


@router.post("/roles/config/{role_id}/test")
async def test_role_config(
    role_id: str,
    body: RoleConfigTestBody | None = None,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    cfg = next(
        (c for c in dashboard.get("roleConfig", []) if c.get("roleId") == role_id),
        None,
    )
    if cfg is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)

    runtime = _merge_test_runtime(
        get_role_runtime_config(session, dashboard, role_id), body
    )
    if not runtime.is_configured:
        raise fail(
            "LLM_NOT_CONFIGURED",
            "请填写并保存 API Base URL、模型 ID 和 API Key",
        )

    try:
        resp = await test_connection(runtime)
    except LlmError as exc:
        raise fail(exc.code, exc.message, status=502) from exc

    return ok(
        {
            "roleId": role_id,
            "model": resp.model,
            "provider": runtime.api_provider,
            "baseUrl": runtime.api_base_url,
            "latencyNote": "连接成功",
            "sample": resp.content[:200],
            "usage": {
                "inputTokens": resp.input_tokens,
                "outputTokens": resp.output_tokens,
            },
        }
    )
