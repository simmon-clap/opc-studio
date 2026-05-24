"""Channel adapter — status, setup, inbound ingress, WeChat outbound."""

from __future__ import annotations

import json

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.api.deps import fail, ok, run_mutation
from app.api.ceo import _run_ceo_chat_background
from app.config import CHANNEL_SECRET, PROJECT_ROOT
from app.db import get_session
from app.presentation.settings import apply_system_settings_patch, get_system_settings
from app.services.channel_auth import verify_channel_token
from app.services.channel_ingress import ingest_channel_message
from app.services.channel_outbound import deliver_wechat_reply_from_session, probe_wechat_gateway, send_wechat_text
from app.services.channel_state import (
    feishu_settings,
    record_feishu_inbound,
    record_wechat_inbound,
    sync_channel_status,
    wechat_settings,
)
from app.services.openclaw_detect import detect_openclaw
from app.services.dashboard_store import get_dashboard, mutate

router = APIRouter(tags=["channels"])

CLAWBOT_CLI = "npx -y @tencent-weixin/openclaw-weixin-cli@latest install"
BRIDGE_DIR = PROJECT_ROOT / "bridge" / "openclaw-opc"


class ChannelInboundBody(BaseModel):
    channel: str = Field(description="wechat | feishu | web")
    text: str = Field(min_length=1)
    senderId: str | None = None
    senderName: str | None = None


class WechatSendBody(BaseModel):
    text: str = Field(min_length=1)
    recipientId: str | None = None


class WechatTestBody(BaseModel):
    text: str = "OPC Studio 渠道测试 — 连接正常 ✓"


def _check_inbound_auth(
    authorization: str | None = Header(default=None),
    x_opc_channel_token: str | None = Header(default=None, alias="X-OPC-Channel-Token"),
) -> None:
    try:
        verify_channel_token(authorization, x_opc_channel_token)
    except ValueError as exc:
        if str(exc) == "UNAUTHORIZED":
            raise fail("UNAUTHORIZED", "渠道 Token 无效", status=401) from exc
        raise


@router.get("/channels/status")
def get_channels_status(session: Session = Depends(get_session)):
    with mutate(session) as dashboard:
        sync_channel_status(dashboard)
        live = dashboard.get("channels") or {}
    configured = get_system_settings(get_dashboard(session)).get("channels") or {}
    wc_cfg = configured.get("wechat") or {}
    fs_cfg = configured.get("feishu") or {}
    return ok(
        {
            "feishu": {
                "connected": bool(live.get("feishu", {}).get("connected")),
                "label": live.get("feishu", {}).get("label", "飞书"),
                "configured": bool((fs_cfg.get("appId") or "").strip()),
                "phase": "2d",
            },
            "wechat": {
                "connected": bool(live.get("wechat", {}).get("connected")),
                "label": live.get("wechat", {}).get("label", "微信"),
                "configured": bool(wc_cfg.get("gatewayUrl") or wc_cfg.get("webhookUrl")),
                "clawbotAvailable": True,
                "lastInboundAt": live.get("wechat", {}).get("lastInboundAt"),
                "lastOutboundAt": live.get("wechat", {}).get("lastOutboundAt"),
            },
            "web": {
                "connected": True,
                "label": live.get("web", {}).get("label", "Web"),
            },
        }
    )


@router.get("/channels/setup")
def get_channels_setup(request: Request):
    base = str(request.base_url).rstrip("/")
    bridge_readme = "/bridge/openclaw-opc/README.md"
    return ok(
        {
            "feishu": {
                "phase": "2d",
                "summary": "飞书企业自建应用 + 事件订阅 Webhook（后续实现）",
                "webhookUrl": f"{base}/api/v1/channels/feishu/webhook",
                "docs": "/docs/CHANNELS-INTEGRATION.md",
                "steps": [
                    "飞书开放平台创建企业自建应用",
                    "事件订阅 URL 指向上方 Webhook（需公网，可用 Cloudflare Tunnel）",
                    "在 OPC 设置页填写 App ID / Secret 并保存",
                ],
            },
            "wechat": {
                "recommended": "clawbot",
                "clawbot": {
                    "summary": "微信官方 ClawBot：终端出二维码，手机微信扫码即可绑定",
                    "cli": CLAWBOT_CLI,
                    "loginCmd": "openclaw channels login --channel openclaw-weixin",
                    "wechatEntry": "微信 → 我 → 设置 → 插件 → ClawBot",
                    "minVersion": {"ios": "8.0.70", "android": "8.0.69"},
                    "note": "扫码绑定的是 OpenClaw ↔ 微信；要让消息进 OPC CEO，需再启动 bridge/openclaw-opc。",
                    "steps": [
                        {
                            "title": "终端安装并扫码",
                            "detail": "在本机终端运行下方命令，终端会显示二维码，用微信扫描并确认授权。",
                            "command": CLAWBOT_CLI,
                        },
                        {
                            "title": "或在手机微信内扫码",
                            "detail": "微信 → 我 → 设置 → 插件 → ClawBot → 扫码绑定（需 iOS 8.0.70+ / Android 8.0.69+ 灰度）。",
                        },
                        {
                            "title": "连接 OPC CEO（本机 Bridge）",
                            "detail": "微信已连 OpenClaw 后，运行 Bridge 将消息转发至 OPC CEO 编排。",
                            "command": "cd bridge/openclaw-opc && npm install && npm start",
                        },
                    ],
                },
                "opcBridge": {
                    "inboundUrl": f"{base}/api/v1/channels/inbound",
                    "bridgeDir": "bridge/openclaw-opc",
                    "bridgeReadme": bridge_readme,
                    "bridgeStart": "cd bridge/openclaw-opc && npm install && npm start",
                    "channelSecretHint": "可选：设置 OPC_CHANNEL_SECRET 并在 Bridge config 中填写相同 token",
                    "example": {
                        "channel": "wechat",
                        "text": "华为 NDA 进展如何？",
                        "senderId": "wx-user-id-from-gateway",
                        "senderName": "Founder",
                    },
                },
                "outbound": {
                    "openclaw": {
                        "sendUrl": "{gatewayUrl}/openclaw/sendmessage",
                        "pollUrl": "{gatewayUrl}/openclaw/getupdates",
                    },
                    "webhook": {
                        "sendUrl": "{webhookUrl}",
                        "note": "兼容 wechat-clawbot-gateway channels.webhook",
                    },
                },
            },
        }
    )


@router.get("/channels/wechat/detect")
def get_wechat_detect(session: Session = Depends(get_session)):
    """Local OpenClaw / ClawBot environment for settings UI."""
    env = detect_openclaw()
    dashboard = get_dashboard(session)
    cfg = wechat_settings(dashboard)
    wc = (dashboard.get("channels") or {}).get("wechat") or {}
    return ok(
        {
            **env,
            "wechatConnected": bool(wc.get("connected")),
            "lastInboundAt": wc.get("lastInboundAt"),
            "savedGatewayUrl": (cfg.get("gatewayUrl") or "").strip(),
        }
    )


@router.post("/channels/inbound")
async def post_channel_inbound(
    body: ChannelInboundBody,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: None = Depends(_check_inbound_auth),
):
    try:

        def _apply(dashboard):
            return ingest_channel_message(
                dashboard,
                channel=body.channel,
                text=body.text,
                sender_id=body.senderId,
                sender_name=body.senderName,
            )

        result, patch = run_mutation(session, _apply, patch_domains=["ceo", "channels", "pulse"])
    except ValueError as exc:
        code = str(exc)
        if code == "EMPTY_MESSAGE":
            raise fail("EMPTY_MESSAGE", "消息不能为空", status=400) from exc
        raise

    async def _chat_and_outbound():
        await _run_ceo_chat_background(body.text, None)
        await deliver_wechat_reply_from_session()

    background_tasks.add_task(_chat_and_outbound)

    dashboard = get_dashboard(session)
    thread = dashboard.get("ceoThread", [])
    return ok(
        {
            "messages": result.get("messages") or (thread[-2:] if len(thread) >= 2 else thread),
            "channel": body.channel,
            "authRequired": bool(CHANNEL_SECRET),
        },
        patch=patch,
        processing=True,
    )


@router.post("/channels/wechat/test")
async def post_wechat_test(
    body: WechatTestBody,
    session: Session = Depends(get_session),
):
    dashboard = get_dashboard(session)
    cfg = wechat_settings(dashboard)
    probe = await probe_wechat_gateway(cfg)
    send_result: dict[str, Any] | None = None
    if probe.get("ok") and cfg.get("outboundEnabled", True):
        has_out = bool((cfg.get("gatewayUrl") or "").strip()) if (cfg.get("outboundMode") or "openclaw") != "webhook" else bool((cfg.get("webhookUrl") or "").strip())
        if has_out:
            recipient = (dashboard.get("channels") or {}).get("wechat", {}).get("lastSenderId")
            send_result = await send_wechat_text(cfg, body.text, recipient_id=recipient)
    with mutate(session) as dash:
        wc = dash.setdefault("channels", {}).setdefault("wechat", {})
        wc["lastProbeOk"] = bool(probe.get("ok"))
        wc["lastProbeAt"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        sync_channel_status(dash)
    return ok({"probe": probe, "send": send_result})


@router.post("/channels/wechat/send")
async def post_wechat_send(body: WechatSendBody, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    cfg = wechat_settings(dashboard)
    recipient = body.recipientId or (dashboard.get("channels") or {}).get("wechat", {}).get(
        "lastSenderId"
    )
    result = await send_wechat_text(cfg, body.text, recipient_id=recipient)
    if not result.get("ok"):
        raise fail(
            "WECHAT_SEND_FAILED",
            result.get("detail") or "微信出站失败",
            status=502,
            details=result,
        )
    return ok(result)


class FeishuSendBody(BaseModel):
    text: str = Field(min_length=1)
    chatId: str | None = None


@router.post("/channels/feishu/webhook")
async def feishu_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise fail("INVALID_JSON", "无效 JSON", status=400)

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    dashboard = get_dashboard(session)
    cfg = feishu_settings(dashboard)
    ts = request.headers.get("X-Lark-Request-Timestamp") or request.headers.get("X-Lark-Request-Time") or ""
    nonce = request.headers.get("X-Lark-Request-Nonce") or ""
    sig = request.headers.get("X-Lark-Signature") or ""
    encrypt_key = (cfg.get("verificationToken") or cfg.get("encryptKey") or "").strip()
    if encrypt_key and sig and not verify_feishu_signature(ts, nonce, body_bytes, encrypt_key, sig):
        raise fail("INVALID_SIGNATURE", "飞书验签失败", status=401)

    parsed = parse_feishu_message_event(payload)
    if not parsed:
        return ok({"ignored": True})

    def _apply(dashboard):
        record_feishu_inbound(
            dashboard, sender_id=parsed.get("senderId"), chat_id=parsed.get("chatId")
        )
        return ingest_channel_message(
            dashboard,
            channel="feishu",
            text=parsed["text"],
            sender_id=parsed.get("senderId"),
            sender_name="Feishu",
        )

    result, patch = run_mutation(session, _apply, patch_domains=["ceo", "channels", "pulse"])
    chat_id = parsed.get("chatId")

    async def _chat_and_reply():
        await _run_ceo_chat_background(parsed["text"], None)
        dash = get_dashboard(session)
        from app.services.channel_outbound import latest_wechat_reply_text

        reply = latest_wechat_reply_text(dash)
        if reply:
            thread = dash.get("ceoThread") or []
            channel = "feishu"
            for msg in reversed(thread):
                if msg.get("direction") == "ceo_to_founder" and msg.get("type") != "ack":
                    channel = msg.get("channel", "feishu")
                    break
            if channel == "feishu":
                cfg2 = feishu_settings(dash)
                await send_feishu_text(cfg2, reply, chat_id=chat_id)
            else:
                await deliver_wechat_reply_from_session()

    background_tasks.add_task(_chat_and_reply)
    return ok({"received": True, "channel": "feishu"}, patch=patch)


@router.post("/channels/feishu/send")
async def post_feishu_send(body: FeishuSendBody, session: Session = Depends(get_session)):
    dashboard = get_dashboard(session)
    cfg = feishu_settings(dashboard)
    chat_id = body.chatId or (dashboard.get("channels") or {}).get("feishu", {}).get("lastChatId")
    result = await send_feishu_text(cfg, body.text, chat_id=chat_id)
    if not result.get("ok"):
        raise fail("FEISHU_SEND_FAILED", result.get("detail") or "飞书发送失败", status=502)
    return ok(result)
