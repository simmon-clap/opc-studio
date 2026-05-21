# OPC Studio

一人公司 Agent 集群 · Mock 看板 + 架构讨论稿。

**仓库：** [github.com/simmon-clap/opc-studio](https://github.com/simmon-clap/opc-studio)

## 快速启动

```bash
cd ~/Documents/opc-agent-framework
chmod +x start.sh   # 首次
./start.sh
# 打开 http://localhost:8765/dashboards/app/
```

> 必须通过 HTTP 访问（不能直接 file:// 打开），否则无法加载 Mock JSON。  
> 若打不开：终端重新运行 `./start.sh`（服务进程退出后需重启）。

## 目录

| 路径 | 说明 |
|------|------|
| [docs/PRD.md](docs/PRD.md) | 产品需求 **v0.3** |
| [docs/API.md](docs/API.md) | **API 契约规范**（前后端对齐基准） |
| [docs/BACKEND.md](docs/BACKEND.md) | Phase 2 后端技术设计 |
| [docs/schemas/](docs/schemas/) | Dashboard JSON Schema |
| [mock/dashboard.json](mock/dashboard.json) | Mock 数据 v0.3.0 |
| [assets/avatars/](assets/avatars/) | 五角色头像 |
| [dashboards/app/](dashboards/app/) | 静态看板 UI |
| [architecture.html](architecture.html) | 业务架构讨论稿 v3 |

## Mock 看板功能（Phase 1 · v0.3 UI）

| Tab | 功能 |
|-----|------|
| **概览** | 公司脉搏条 + 五角色节点 + 协作连线 + 加厚角色详情（任务/活动流） |
| **项目** | Pipeline 统计 + 项目卡片（含盈亏摘要）+ **项目工作室** |
| **客户** | 客户档案、关联项目、沟通纪要、收款 |
| **收件箱** | 必读 / 请示 / 待批 + 待办·已办·归档 + HITL 批准/驳回 |
| **经营** | 收入 / Token 成本 / **毛利** / **项目盈亏** / 按角色·周 |
| **周报** | CEO 一页纸 + Pipeline·待决·经营快照 |
| **CEO FAB** | 简报投递、飞书/企微/Web 渠道 Mock |
| **设置** | 五角色模型/API/预算/工具 |

**结项流程（Mock）：** HITL-3 批准 → 结项清单 → 导出客户 ZIP

## 文档状态

- [x] PRD v0.3（与 Mock 看板对齐）
- [x] Mock 数据 + 静态看板
- [x] Phase 2 后端设计草案（[BACKEND.md](docs/BACKEND.md)）
- [x] API 契约 v1.0（[API.md](docs/API.md) + Mock 黄金样本）
- [ ] Phase 2a 后端实现
- [ ] Phase 3 真 Agent
