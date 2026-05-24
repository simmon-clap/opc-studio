# 设置 & 执行平台 · 实现说明

| 版本 | v0.9.x |
| 状态 | **Epic 1–2 ✅ · Epic 3–5 ⚠️（后端主体 + 部分 UI）** · [DEV-STATUS.md](./DEV-STATUS.md) |
| 测试 | `pytest` **160 passed** |

## 新增 Dashboard 域

| 域 | 说明 |
|----|------|
| `roleRegistry` | 动态角色注册（bootstrap 五角色，不 seed brand） |
| `roleProfiles` | 每角色 Markdown Profile |
| `systemSettings` | 编排配置（双写 `meta.runtimeSettings`） |
| `skillCatalog` | Skill Hub 目录 |
| `skillChains` | Skill 链定义 |
| `mcpConnections` | MCP 连接 |

## API 索引

| 分组 | 端点 |
|------|------|
| 设置 | `GET /settings/summary` · `GET/PATCH /system/settings` |
| 角色 | `GET/POST /roles/registry` · `PATCH /roles/{id}/identity` · `GET/PUT /roles/{id}/profile` · **`POST /roles/{id}/avatar`** |
| 工具 | `GET /tools` · `GET /tools/effective/{roleId}` |
| Skill | `GET /skills` · `POST /skills/import` · `POST /skills/{id}/activate` |
| Skill 链 | `GET/POST /skill-chains` |
| MCP | `GET/POST /mcp/connections` · `POST /mcp/connections/{id}/health`（**stub**） |
| 运行 | `GET /agent-runs/{id}/trace` |
| Inbox | `POST /inbox/{id}/skill-install` |
| 渠道 | `GET /channels/status` · `GET /channels/setup` · `POST /channels/inbound` |

## 前端

- `dashboards/app/js/settings.js` — 系统/角色 segment（`.stg-*` / `.fin-segment`）
- `isSettingsUiInteractive()` — Pulse 防闪退
- Skill Hub 列表 + 导入 Modal；MCP 添加；角色 enabledSkills 勾选
- 分槽 Model 独立 URL/Key；头像「更换」
- ClawBot 渠道指引 + CLI 复制

## 后端模块

| 模块 | 路径 |
|------|------|
| 角色注册 | `app/presentation/roles_registry.py` |
| 设置同步 | `app/presentation/settings.py` |
| Skill | `app/presentation/skills.py` |
| MCP | `app/presentation/mcp.py` · `app/mcp/bridge.py`（**stub**） |
| Tool Registry | `app/tools/registry.py` |
| Agent Loop | `app/runners/agent_loop.py` |
| Skill 链 | `app/orchestrator/skill_chain.py` |
| 头像 | `app/services/avatar_storage.py` · `app/api/roles.py` |
| 分槽 Key | `app/security/role_credentials.py` |
| 渠道 | `app/api/channels.py` · `app/services/channel_ingress.py` |

## 测试文件

- `test_roles_registry.py`
- `test_tools_registry.py`
- `test_skill_hub.py`
- `test_mcp_bridge.py`
- `test_skill_chain.py`
- `test_avatar_channels.py`
- `test_role_config_masks.py`

## 未完成（见 DEV-STATUS §3.3–3.4）

- MCP stdio 真子进程（当前 stub health）
- image/video slot 真实 media_client
- 设置页 Skill 详情 drawer · 链编辑器 UI · Tool allow/deny chips
- `skill_proposal` 收件箱专用 Modal · Brief 附件自动提案
- `meta.skillRoutes` 设置页可视化编辑
- 编排高级 UI（pauseWhileCeoThread · Proposal 日上限）
