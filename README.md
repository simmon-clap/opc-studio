# OPC Studio

一人公司 Agent 集群 · Web 看板 + FastAPI 后端 + Agent 编排。

**仓库：** [github.com/simmon-clap/opc-studio](https://github.com/simmon-clap/opc-studio)

## 快速启动

```bash
cd ~/Documents/opc-agent-framework
chmod +x start.sh   # 首次
./start.sh
# 打开 http://127.0.0.1:8765/dashboards/app/
# API 文档 http://127.0.0.1:8765/docs
```

首次启动会自动创建 `.venv`、安装依赖、从 `mock/dashboard.json` 种子灌库到 `data/`。

## 目录

| 路径 | 说明 |
|------|------|
| [backend/](backend/) | FastAPI + SQLite + Orchestrator |
| [dashboards/app/](dashboards/app/) | 看板前端 |
| [mock/dashboard.json](mock/dashboard.json) | 契约黄金样本 |
| [docs/DEV-STATUS.md](docs/DEV-STATUS.md) | **开发状态 SSOT**（已完成 / 未完成 backlog） |
| [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) | 全链路开发计划 v2.0 |
| [docs/AGENTS.md](docs/AGENTS.md) | Agent 编排设计 |
| [docs/API.md](docs/API.md) | API 契约 |
| [reference/from-cluster/](reference/from-cluster/) | 早期原型文档（Charter/SOP/红线，只读参考） |

## 已实现

> 完整 backlog 见 [docs/DEV-STATUS.md](docs/DEV-STATUS.md)

| 阶段 | 状态 |
|------|------|
| Phase 1 Mock 看板 | ✅ |
| Phase 2a–c 控制面 API | ✅ |
| Phase 2e 角色配置 · 头像 · 分槽 Key | ✅ |
| Phase 3a–f 编排骨架 + Runners + 会诊 API | ✅（Stub 默认；配 Key 可走 LLM） |
| Pulse/Agency · 设置 Epic 1–2 | ✅ |
| 设置 Epic 3–5 · 渠道 inbound | ⚠️ 后端主体；UI/MCP/飞书全链路缺 |
| Phase 2d / 4 飞书 Webhook + 出站 | ❌ |

## 开发

```bash
cd backend && source .venv/bin/activate
pytest -q
```

## 版本与发版

- 版本号：根目录 [`VERSION`](VERSION)（单一来源）
- 发版前：`chmod +x scripts/*.sh && ./scripts/release-check.sh`
- 备份数据：`./scripts/backup-data.sh`
- 部署说明：[`deploy/README.md`](deploy/README.md)（含 Cloudflare Tunnel / VPS）

## 环境变量

见 [.env.example](.env.example)：`OPC_DATA_DIR`、`OPC_SECRET_KEY`、`OPC_PORT`。
