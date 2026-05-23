# 经营 v2 规范

> 经营 = **财务/Ops 维护的经营账本**；CEO 汇总合同与决策，法务手工维护税率/合规项。与周报、工作室、客户严格分工。

## 1. 边界

| Tab | 职责 | 经营页禁止 duplicate |
|-----|------|---------------------|
| **经营** | 实时 P&L、项目盈亏、角色 Token 成本、报表导出 | — |
| 周报 | 本周叙事结论 | ❌ 完整损益表（仅 1 句 + ≤2 指标 + `costsLink`） |
| 项目工作室 | 交付与产出 | ❌ 完整 P&L（仅 header `pnlHealth` tag） |
| 客户 | 合同/收款 CRM | ❌ 客户列表（仅链 `clientId`） |
| 收件箱 | 拍板/HITL | ❌ 待收交互矩阵 |

**维护分工**

| 角色 | 输入 |
|------|------|
| CEO | 合同金额、报价、项目阶段 |
| Ops/财务 | `costs` domain 维护、期间切换、导出 |
| 法务 | 手工 `taxRatePct` / `costBreakdown.tax` |
| 系统自动 | Agent Run → Token 成本、`byRole` / 项目 `byRole` 汇总 |

## 2. 信息预算（硬上限）

### 2.1 公司概览（首屏）

| 区块 | 上限 | 呈现 |
|------|------|------|
| 简化损益表 | **6 行** | 营业收入 → 营业成本 → **毛利** → 期间费用 → **经营利润** → 现金（已收/待收） |
| Token 预算 | 1 环 + 2 数字 | 已用 / 预算 / 剩余 |
| 告警 | 0–1 条 | 预算超支 / 需关注项目数 |

### 2.2 项目列表

| 项 | 上限 |
|----|------|
| 卡片 | 名称 · 健康度 · 合同/报价 · 成本 · 毛利 · **1 行建议** |
| 筛选 | 全部 / 盈利 / 需关注 / 线索 |

### 2.3 项目详情 Modal

| 区块 | 上限 |
|------|------|
| 财务快照 | 6 行 |
| 按角色成本 | role 汇总（Token + 占比），**无 run 级钻取** |
| 成本明细 | Token / 外部 / 税费 / 其他（折叠） |
| 财务建议 | **1 段 ≤120 字**（`advisory`） |

## 3. UI 结构

### 3.1 列表页（`/costs` Tab）

```
┌──────────────────────────────────────────────────┐
│ [2026-05 ▾] [月度|季度]              [导出 XLSX ▾] │
├──────────────────────────────────────────────────┤
│ 简化损益表（6 行 + 结构条）                        │
│ Token 预算环 │ 告警                               │
├──────────────────────────────────────────────────┤
│ 项目盈亏 · 筛选 chips · 卡片列表                  │
├──────────────────────────────────────────────────┤
│ 按角色成本（<details> 可折叠）                     │
│ 近四周 Token（<details> 可折叠）                   │
└──────────────────────────────────────────────────┘
```

- 移除重复的三卡 KPI + Token chip 网格（并入损益表与项目卡）
- 导出走 API，顶栏下拉

### 3.2 项目详情 Modal

顶栏：项目名 · 健康度 · **关闭**  
正文：财务快照 → 按角色成本 → 成本明细 → 建议 → 链工作室/客户

### 3.3 跨 Tab 联动

- 周报 `costsLink` → 经营 Tab
- 项目卡 `pnlHealth` → `showProjectPnL()`
- Pulse：`isFinanceUiInteractive()` 时跳过重绘

## 4. 数据模型

```json
{
  "costs": {
    "period": "2026-05",
    "periodType": "month",
    "currency": "CNY",
    "maintainedBy": "ops",
    "lastSyncedAt": "ISO8601",

    "statement": {
      "revenue": 76000,
      "costOfServices": 2840,
      "grossProfit": 73160,
      "grossMarginPct": 96.3,
      "operatingExpenses": 300,
      "operatingProfit": 72860,
      "cashReceived": 52000,
      "cashPending": 24000,
      "taxAccrual": 0,
      "taxRatePct": null
    },

    "summary": { "...": "兼容镜像，由 sync_finance 写入" },

    "byProject": [{
      "projectId": "proj-acme",
      "clientId": "client-acme",
      "tokens": 520000,
      "cost": 1680,
      "costBreakdown": {
        "token": 1680,
        "external": 0,
        "tax": 0,
        "other": 0
      },
      "byRole": [
        { "roleId": "dev", "tokens": 380000, "cost": 1200, "runs": 62, "sharePct": 71.4 }
      ],
      "revenue": 48000,
      "received": 24000,
      "pending": 24000,
      "margin": 46320,
      "marginPct": 96.5,
      "health": "healthy",
      "advisory": "按合同口径盈利；建议跟进待收 ¥24,000",
      "advisorySource": "rule"
    }],

    "byRole": [ "..." ],
    "weekly": [ { "week": "2026-W20", "cost": 900 } ],
    "meta": {
      "budgetAlertThresholdPct": 80,
      "lossProjectCount": 0,
      "watchProjectCount": 1
    }
  }
}
```

**健康度规则（自动）**

| health | 条件 |
|--------|------|
| `pipeline` | `revenue=0` 且（有 `quoted` 或项目 stage=lead） |
| `watch` | 未签约但已有成本；或已签约 `received < cost` |
| `loss` | 已签约且 `margin < 0` |
| `healthy` | `marginPct ≥ 70` 且 `received ≥ cost` |
| `strong` | `marginPct ≥ 90` 且 `pending = 0` |

**税率**：法务手工 PATCH `taxRatePct` 或项目 `costBreakdown.tax`；不做自动规则。

## 5. API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/finance/summary` | `statement` + `summary` + `meta` + 期间信息 |
| GET | `/api/v1/finance/projects` | 项目盈亏列表 |
| GET | `/api/v1/finance/projects/{id}` | 项目详情 + `byRole` + `costBreakdown` |
| PATCH | `/api/v1/finance/period` | `{ periodType, period }` 切换月/季 |
| PATCH | `/api/v1/finance/projects/{id}` | 财务维护：`costBreakdown`、`advisory`、`taxRatePct` |
| GET | `/api/v1/finance/export?format=xlsx&scope=full` | XLSX 多 Sheet 导出（stdlib 生成，无需额外依赖） |

**XLSX Sheet**

1. 损益摘要  
2. 项目明细  
3. 角色 Token（含项目维度）  
4. 收款明细（`payments`）

## 6. 同步链路

```
sync_finance(dashboard)
  ├─ payments → byProject.revenue/received/pending
  ├─ costBreakdown → project.cost
  ├─ 重算 health + advisory（规则）
  ├─ 按期间过滤 → statement
  ├─ mirror → summary（兼容）
  └─ 更新当前周报草稿 finance block（≤2 指标）
```

**调用点**：`GET /dashboard`（persist）、`record_agent_cost` 后、`PATCH /finance/*`

## 7. 交互防闪退

Modal 打开 / 期间下拉 / `<details>` 展开 / 导出菜单展开时，Pulse **只更新内存、不重绘**（`isFinanceUiInteractive()`）。
