#!/usr/bin/env node
/**
 * OpenClaw ↔ OPC Studio Bridge
 *
 * Polls OpenClaw Gateway (ClawBot / wechat-clawbot-gateway openclaw server)
 * and forwards user messages to POST /api/v1/channels/inbound.
 *
 * CEO replies are pushed by OPC directly to gateway /openclaw/sendmessage —
 * this process only handles inbound (WeChat → OPC).
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONFIG_PATH = process.env.OPC_BRIDGE_CONFIG || path.join(__dirname, "config.json");

function loadConfig() {
  const example = path.join(__dirname, "config.example.json");
  if (!fs.existsSync(CONFIG_PATH)) {
    if (fs.existsSync(example)) {
      fs.copyFileSync(example, CONFIG_PATH);
      console.log(`[bridge] Created ${CONFIG_PATH} from example — edit before production.`);
    } else {
      throw new Error("Missing config.json");
    }
  }
  return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
}

function extractText(msg) {
  const items = msg?.item_list || [];
  for (const item of items) {
    if (item.type === 1 && item.text_item?.text) return item.text_item.text.trim();
  }
  return "";
}

async function postOpcInbound(cfg, { text, senderId, senderName }) {
  const headers = { "Content-Type": "application/json" };
  if (cfg.opcChannelToken) {
    headers.Authorization = `Bearer ${cfg.opcChannelToken}`;
    headers["X-OPC-Channel-Token"] = cfg.opcChannelToken;
  }
  const res = await fetch(cfg.opcInboundUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({
      channel: "wechat",
      text,
      senderId,
      senderName: senderName || cfg.defaultSenderName || "Founder",
    }),
  });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`OPC inbound ${res.status}: ${body.slice(0, 200)}`);
  }
  return body;
}

async function pollOpenClaw(cfg) {
  const base = cfg.openclawGatewayUrl.replace(/\/$/, "");
  const headers = { "Content-Type": "application/json" };
  if (cfg.openclawToken) headers.Authorization = `Bearer ${cfg.openclawToken}`;
  const res = await fetch(`${base}/openclaw/getupdates`, {
    method: "POST",
    headers,
    body: JSON.stringify({ timeout: cfg.longPollTimeoutSec ?? 25 }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`getupdates ${res.status}: ${t.slice(0, 200)}`);
  }
  return res.json();
}

async function main() {
  const cfg = loadConfig();
  console.log("[bridge] OPC inbound:", cfg.opcInboundUrl);
  console.log("[bridge] OpenClaw gateway:", cfg.openclawGatewayUrl);
  console.log("[bridge] Waiting for WeChat messages…");

  while (true) {
    try {
      const data = await pollOpenClaw(cfg);
      const msgs = data?.msgs || [];
      for (const msg of msgs) {
        const text = extractText(msg);
        const senderId = msg.from_user_id || msg.fromUserId;
        if (!text) continue;
        console.log(`[bridge] ← wechat/${senderId}: ${text.slice(0, 80)}`);
        const reply = await postOpcInbound(cfg, {
          text,
          senderId,
          senderName: cfg.defaultSenderName,
        });
        console.log("[bridge] → OPC ok", reply.slice(0, 120));
      }
    } catch (err) {
      console.error("[bridge] error:", err.message || err);
    }
    await new Promise((r) => setTimeout(r, cfg.pollIntervalMs ?? 500));
  }
}

main();
