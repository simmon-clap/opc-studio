# 周报 v2 规范

> 周报 = **回顾发布物**，不是工作台。与收件箱、项目、经营严格分工。

## 1. 边界

| Tab | 职责 | 周报禁止 duplicate |
|-----|------|-------------------|
| 收件箱 | 待办、拍板、HITL、请示 | ❌ 待你拍板、决策 chip |
| 项目 | 实时进度、工作室 | ❌ Pipeline 操作台 |
| 经营 | 实时 P&L、明细 | ❌ 四行财务表 |
| **周报** | CEO 对**本周**的叙事结论 | — |

- 发送后 **冻结**（`status: sent`）；草稿可「重新生成」，须记录 `snapshotAt`。
- 待办仅可在正文 **文字提及** + 链到收件箱，不做交互矩阵。

## 2. 信息预算（硬上限）

| 区块 `kind` | 上限 | 呈现 |
|-------------|------|------|
| `summary` | ≤120 字 | 纯文字 |
| `projects` | ≤5 项 | 进度条 + 1 行 bullet |
| `risks` | ≤3 项 | 🟢🟡🔴 + 1 行 |
| `finance` | 1 句 + ≤2 指标 | 链出经营 Tab |
| `outlook` | ≤3 条 | 有序列表 |
| `highlights` | 每 role ≤1 行 | **默认折叠** |

超出 → 不进入周报，留在源 Tab。

## 3. UI 结构

### 3.1 列表页（`/weekly` Tab）

- **概览条**（顶部一条）：当前期 `周次 · 状态 · 周期` + CEO 总述 + 轻量 chips（在跟项目数 / 需关注风险数）；点击进入详情 Modal
- **历史列表**：周次 + 状态 + summary 截断（最近 8 周，更早折叠）；不含概览已展示的当前期
- 无 Hero 大屏、无 KPI 面板、无页内导出/发送

### 3.2 详情 Modal

顶栏：`W20 · 周期 · 状态` + **发送**（仅草稿）与 **关闭** 并排；无导出按钮（导出走 API，不进 Modal UI）

正文顺序（F 型 90 秒扫读）：

1. 总述
2. 项目进展（`projects`）
3. 风险与关注（`risks`）
4. 本周经营（`finance`）
5. 下周重点（`outlook`）
6. 部门一句（`highlights`，`<details>` 默认关）

**Role 头像**：仅 **section 标题行** 一个头像（`block.roleId`），子项不用头像。

### 3.3 收件箱

必读项「W20 周报草稿」→ **直接打开详情 Modal**，不在 Inbox 内嵌半页正文。

## 4. 数据模型

```json
{
  "weeklyReports": [
    {
      "id": "2026-W20",
      "week": "2026-W20",
      "period": "2026-05-19 ~ 2026-05-25",
      "status": "draft",
      "generatedAt": "ISO8601",
      "snapshotAt": "ISO8601",
      "author": "ceo",
      "summary": "一句总述",
      "blocks": [
        {
          "kind": "projects",
          "title": "项目进展",
          "roleId": "ceo",
          "items": [
            {
              "projectId": "proj-acme",
              "label": "Acme",
              "progress": 78,
              "text": "staging 完成，交付待批"
            }
          ]
        },
        {
          "kind": "risks",
          "title": "风险与关注",
          "roleId": "ceo",
          "items": [
            { "level": "medium", "text": "Beta ERP 私有部署" }
          ]
        },
        {
          "kind": "finance",
          "title": "本周经营",
          "roleId": "ops",
          "text": "毛利与上周持平；无新增收款",
          "metrics": [
            { "label": "毛利", "value": "96.3%" }
          ],
          "costsLink": true
        },
        {
          "kind": "outlook",
          "title": "下周重点",
          "roleId": "ceo",
          "items": ["Acme 结项", "Beta PoC 启动"]
        },
        {
          "kind": "highlights",
          "title": "部门一句",
          "roleId": "ceo",
          "collapsed": true,
          "items": [
            { "roleId": "dev", "text": "Acme staging 自测 4/5" }
          ]
        }
      ]
    }
  ],
  "weeklyReport": { }
}
```

- `weeklyReport`：兼容字段，= 当前草稿或最新一期（由 `sync_weekly_reports` 维护）。
- **废弃**（v2 UI 不渲染）：`pendingDecisions`、`pipelineSnapshot`、`rolePerformance`、`sections[]` 长文。

## 5. API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/weekly` | 列表（轻量 `items[]`） |
| GET | `/api/v1/weekly/current` | 当前草稿或最新 |
| GET | `/api/v1/weekly/{id}` | 详情 |
| POST | `/api/v1/weekly/current/send` | 发送当前草稿 |
| GET | `/api/v1/weekly/current/export?format=md` | 导出 |

## 6. 交互防闪退

与工作室一致：Modal 打开 / 下拉展开 / `<details>` 展开时，Pulse 刷新 **只更新内存数据、不重绘 DOM**（`isWeeklyUiInteractive()`）。
