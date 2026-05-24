"""Role configuration endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from app.api.deps import fail, ok
from app.db import get_session
from app.presentation.roles_registry import (
    CAPABILITIES,
    create_registry_role,
    migrate_role_config_models,
    patch_registry_role,
    patch_role_identity,
    registry_entry,
    registry_summary,
)
from app.security.role_credentials import SLOT_KEYS, get_slot_runtime, patch_slot
from app.security.secrets import mask_api_key
from app.services.avatar_storage import save_role_avatar
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
    models: dict[str, Any] | None = None
    enabledSkills: list[str] | None = None
    toolPolicy: dict[str, list[str]] | None = None


class RoleConfigTestBody(BaseModel):
    """测试连接时可传入表单当前值（不必先落库）。"""
    model: str | None = None
    apiProvider: str | None = None
    apiBaseUrl: str | None = None
    apiKey: str | None = None
    capability: str = "text"


class RegistryCreateBody(BaseModel):
    id: str = Field(min_length=2, max_length=25)
    name: str = Field(min_length=1)
    title: str | None = None
    department: str | None = None
    capabilities: list[str] = Field(default_factory=lambda: ["text"])
    dispatchable: bool = True
    shortLabel: str | None = None

    @field_validator("id")
    @classmethod
    def validate_role_id(cls, value: str) -> str:
        from app.presentation.roles_registry import ROLE_ID_PATTERN

        role_id = value.strip().lower()
        if not ROLE_ID_PATTERN.match(role_id):
            raise ValueError("须以小写字母开头，仅含 a-z、0-9、_、-，2–25 位")
        return role_id


class RegistryPatchBody(BaseModel):
    status: str | None = None
    dispatchable: bool | None = None
    capabilities: list[str] | None = None
    department: str | None = None
    shortLabel: str | None = None


class IdentityPatchBody(BaseModel):
    name: str | None = None
    title: str | None = None
    department: str | None = None
    charter: str | None = None
    avatar: str | None = None


class ProfileBody(BaseModel):
    document: str


def _merge_test_runtime(runtime, body: RoleConfigTestBody | None):
    if body is None:
        return runtime
    from dataclasses import replace

    cap = (body.capability if body else None) or "text"
    merged = replace(
        runtime,
        model=body.model or runtime.model,
        api_provider=body.apiProvider or runtime.api_provider,
        api_base_url=(body.apiBaseUrl or runtime.api_base_url).rstrip("/"),
        api_key=body.apiKey or runtime.api_key,
    )
    return merged


def _apply_slot_secrets_to_config(item: dict, row: RoleSecret | None) -> None:
    models = item.setdefault("models", {})
    for cap in SLOT_KEYS:
        slot = models.setdefault(cap, {})
        runtime = get_slot_runtime(row, cap)
        if runtime.get("api_base_url"):
            slot["apiBaseUrl"] = runtime["api_base_url"]
        slot["apiKeyConfigured"] = runtime["api_key_configured"]
        masked = mask_api_key(runtime["api_key"]) if runtime["api_key"] else None
        slot["apiKeyMasked"] = masked["masked"] if masked else None


def _build_role_config(session: Session, dashboard: dict) -> list[dict]:
    configs = []
    for cfg in dashboard.get("roleConfig", []):
        role_id = cfg.get("roleId")
        migrate_role_config_models(cfg)
        row = session.get(RoleSecret, role_id) if role_id else None
        role = next(
            (r for r in dashboard.get("roles", []) if r.get("id") == role_id),
            {},
        )
        item = dict(cfg)
        if not (item.get("rolePrompt") or "").strip():
            profile_doc = (
                (dashboard.get("roleProfiles") or {}).get(role_id or "", {}).get("document") or ""
            ).strip()
            if profile_doc:
                item["rolePrompt"] = profile_doc
            else:
                item["rolePrompt"] = default_role_prompt(
                    role_id or "",
                    role.get("name") or role_id or "",
                    role.get("charter") or "",
                )
        _apply_slot_secrets_to_config(item, row)
        # Legacy flat fields for backward compat
        text = (item.get("models") or {}).get("text") or {}
        item["model"] = text.get("model") or item.get("model") or ""
        item["apiProvider"] = text.get("apiProvider") or item.get("apiProvider") or "OpenRouter"
        item["apiBaseUrl"] = text.get("apiBaseUrl") or item.get("apiBaseUrl") or "https://openrouter.ai/api/v1"
        item["apiKeyConfigured"] = bool(text.get("apiKeyConfigured"))
        masked = text.get("apiKeyMasked")
        item["apiKey"] = {"masked": masked} if masked else None
        configs.append(item)
    return configs


@router.get("/roles/registry")
def get_roles_registry(session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    return ok(registry_summary(dashboard))


@router.post("/roles/registry")
def post_roles_registry(body: RegistryCreateBody, session: Session = Depends(get_session)):
    invalid = [c for c in body.capabilities if c not in CAPABILITIES]
    if invalid:
        raise fail("INVALID_CAPABILITY", f"不支持的能力：{', '.join(invalid)}")
    try:
        with mutate(session) as dashboard:
            entry = create_registry_role(dashboard, body.model_dump())
    except ValueError as exc:
        code = str(exc)
        if code == "ROLE_EXISTS":
            raise fail("ROLE_EXISTS", "角色 ID 已存在", status=409) from exc
        raise fail("INVALID_ROLE_ID", "角色 ID 格式无效", status=400) from exc
    return ok(entry)


@router.patch("/roles/registry/{role_id}")
def patch_roles_registry(
    role_id: str, body: RegistryPatchBody, session: Session = Depends(get_session)
):
    with mutate(session) as dashboard:
        entry = patch_registry_role(dashboard, role_id, body.model_dump(exclude_none=True))
    if entry is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    return ok(entry)


@router.patch("/roles/{role_id}/identity")
def patch_role_identity_endpoint(
    role_id: str, body: IdentityPatchBody, session: Session = Depends(get_session)
):
    with mutate(session) as dashboard:
        role = patch_role_identity(dashboard, role_id, body.model_dump(exclude_none=True))
    if role is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    return ok(role)


@router.post("/roles/{role_id}/avatar")
async def upload_role_avatar(
    role_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    if registry_entry(dashboard, role_id) is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    raw = await file.read()
    try:
        avatar_url = save_role_avatar(role_id, raw, file.content_type)
    except ValueError as exc:
        code = str(exc)
        if code == "FILE_TOO_LARGE":
            raise fail("FILE_TOO_LARGE", "头像过大（最大 5MB）", status=413) from exc
        if code == "UNSUPPORTED_FORMAT":
            raise fail("UNSUPPORTED_FORMAT", "仅支持 PNG / JPEG / WebP / GIF", status=400) from exc
        if code == "EMPTY_FILE":
            raise fail("EMPTY_FILE", "文件为空", status=400) from exc
        raise
    with mutate(session) as dashboard:
        role = patch_role_identity(dashboard, role_id, {"avatar": avatar_url})
    if role is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    return ok({"roleId": role_id, "avatar": avatar_url, "role": role})


@router.get("/roles/{role_id}/profile")
def get_role_profile(role_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    if registry_entry(dashboard, role_id) is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    profile = (dashboard.get("roleProfiles") or {}).get(role_id) or {
        "document": "",
        "updatedAt": None,
    }
    return ok({"roleId": role_id, **profile})


@router.put("/roles/{role_id}/profile")
def put_role_profile(
    role_id: str, body: ProfileBody, session: Session = Depends(get_session)
):
    now = datetime.now(timezone.utc).isoformat()

    def _apply(dashboard):
        if registry_entry(dashboard, role_id) is None:
            raise ValueError("ROLE_NOT_FOUND")
        profiles = dashboard.setdefault("roleProfiles", {})
        profiles[role_id] = {"document": body.document, "updatedAt": now}
        return profiles[role_id]

    with mutate(session) as dashboard:
        try:
            result = _apply(dashboard)
        except ValueError as exc:
            raise fail("ROLE_NOT_FOUND", "角色不存在", status=404) from exc
    return ok({"roleId": role_id, **result})


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


@router.get("/roles/config/{role_id}")
def get_role_config(role_id: str, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    cfg = next(
        (c for c in _build_role_config(session, dashboard) if c.get("roleId") == role_id),
        None,
    )
    if cfg is None:
        raise fail("ROLE_NOT_FOUND", "角色不存在", status=404)
    return ok(cfg)


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
        migrate_role_config_models(target)
        slot_key_patches: list[tuple[str, str | None, str | None]] = []
        # Flat model fields → models.text
        if "model" in updates:
            target.setdefault("models", {}).setdefault("text", {})["model"] = updates.pop("model")
        if "apiProvider" in updates:
            target.setdefault("models", {}).setdefault("text", {})["apiProvider"] = updates.pop(
                "apiProvider"
            )
        if "apiBaseUrl" in updates:
            base = updates.pop("apiBaseUrl")
            target.setdefault("models", {}).setdefault("text", {})["apiBaseUrl"] = base
            slot_key_patches.append(("text", base, None))
        if "models" in updates:
            models_patch = updates.pop("models")
            base_models = target.setdefault("models", {})
            for slot, slot_val in models_patch.items():
                if not isinstance(slot_val, dict):
                    continue
                slot_key = slot_val.pop("apiKey", None)
                base_url = slot_val.get("apiBaseUrl")
                base_models.setdefault(slot, {}).update(slot_val)
                if slot_key or base_url is not None:
                    slot_key_patches.append((slot, base_url, slot_key))
        for key, value in updates.items():
            target[key] = value

    row = session.get(RoleSecret, role_id)
    now = datetime.now(timezone.utc)
    if row is None:
        row = RoleSecret(role_id=role_id, updated_at=now)
    if api_key:
        patch_slot(row, "text", api_key=api_key)
    for cap, base_url, slot_key in slot_key_patches:
        patch_slot(
            row,
            cap,
            api_base_url=base_url if base_url is not None else None,
            api_key=slot_key,
        )
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
        get_role_runtime_config(
            session, dashboard, role_id, capability=(body.capability if body else "text")
        ),
        body,
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

    cap = (body.capability if body else None) or "text"
    return ok(
        {
            "roleId": role_id,
            "capability": cap,
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
