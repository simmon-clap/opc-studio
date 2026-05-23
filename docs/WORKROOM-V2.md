# Workroom v2 · 项目工作室规范

| 项 | 内容 |
|----|------|
| 版本 | **v2.0** |
| 状态 | **已实现** |
| 关联 | [PRD.md](./PRD.md) §3 · [API.md](./API.md) |

---

## 1. 定位

**工作室 = 单项目的交付操作台**，不是经营看板。

| 在这里 | 不在这里 |
|--------|----------|
| 按阶段浏览交付物 | 项目盈亏（→ 经营 Tab） |
| 阅读 / 填写 / 批准交付 | 批量 HITL（→ 收件箱） |
| 当前焦点与流程提醒 | 全公司 KPI |

**HITL 双通道：** 工作室可对 **当前交付** 批准/驳回；收件箱做 **批量与跨项目** 待办。

**部署：** 上云友好，下载一律 HTTP（MD / PDF / ZIP），不提供「打开本地文件夹」。

---

## 2. 布局

```
顶栏：← 客户名 · 阶段 · 进度% [待批点] ············· [项目 ↓]
├─ 左栏（240px）阶段分组 + 交付列表 + 折叠会诊/结项/Brief
└─ 中栏
   ├─ 当前焦点条（1 条 highlight + 其余折叠）
   ├─ 交付标题 + [交付 ↓]
   ├─ 操作条（Agent / Founder）
   └─ Viewer
```

---

## 3. 左栏 · 流程树

分组顺序（不变）：评估 · 立项 → 法务 · 合同 → 工程 · 交付 → 验收 · 结项 → 运营 · 台账。

### 交付状态点

| 符号 | `status` / 条件 |
|------|------------------|
| ⏳ | `review` 或有待填 |
| ● | `approved` |
| ↻ | `revision` |
| ○ | `draft` / 其他 |
| — | workflow 占位，尚无 artifact |

### 折叠节点

| 节点 | 出现条件 | 挂载阶段 |
|------|----------|----------|
| Brief · N 项待确认 | `openQuestions` 非空 | 评估 · 立项 |
| CEO 会诊 | 有 deliberation turns | 评估 · 立项 |
| 结项清单 · x/y | `closure` 存在 | 验收 · 结项 |

---

## 4. 顶栏

- **标题：** 客户名
- **进度：** `{stage}` + `{progress}%`；若 `hitlPending` 显示橙点「待你批」
- **项目 ↓：** 唯一项目级下载（内部 ZIP / 客户 ZIP）

---

## 5. 当前焦点

API：`GET /projects/{id}/next-steps` → `{ focus, others }`

优先级：

1. `hitl` — 待 Founder 审批
2. `fill` — Brief 或 artifact 待填
3. `running` — Agent task 执行中
4. `pending` — 队列待执行
5. `process` / `question` / `commitment` — 流程 cue

---

## 6. 交付操作条

由 `artifact.actions[]` 驱动（服务端计算）：

| 状态 | 典型 actions |
|------|----------------|
| `review` + hitlId | approve, reject |
| `draft` + 待填 | edit, submit_review |
| `approved` | （无 primary，下载在 ↓） |

---

## 7. 下载

### 交付 ↓

- Markdown
- PDF（文档类）
- 版本 ZIP（含 files[]）
- 复制 Demo 链接（若有）

### 项目 ↓

- 内部完整包 `?type=internal`
- 客户交付包 `?type=client`（结项时）

---

## 8. API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects/{id}/workroom` | 聚合：project、groups、focus、deliberation、closure |
| GET | `/projects/{id}/next-steps` | `{ focus, others }` |
| PATCH | `/projects/{id}` | 更新 priority / summary / assignees（priority 同步 task + 通知 CEO） |
| PATCH | `/projects/{id}/brief` | 更新 openQuestions / scope 等 Brief 字段 |
| GET | `/projects/{id}/artifacts/{aid}` | 含 `actions`, `exportFormats` |

---

## 9. 与 v0.3 差异

| 移除 | 替代 |
|------|------|
| 工作室 P&L 条 | 经营 Tab |
| 中间 Brief / 下一步 / 会诊 / 结项 panel | 左栏折叠 + 焦点条 |
| 顶栏 MD/PDF/ZIP 三 icon | 项目 ↓ + 交付 ↓ |
