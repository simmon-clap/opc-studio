# 设置 v2 规范

> 设置 = **控制面**。系统偏好与编排在一处；角色身份、Profile、模型、Skill 绑定在另一处。UI 与周报/经营同级：克制、分段、可扫读。

| 状态 | **Epic 1–2 ✅ · 细项见 [DEV-STATUS §3.3](./DEV-STATUS.md#33-p1--设置--skill-ui)** |
|------|------|
| 关联 | [SETTINGS-PLATFORM-ROADMAP.md](./SETTINGS-PLATFORM-ROADMAP.md) · [SETTINGS-IMPLEMENTATION.md](./SETTINGS-IMPLEMENTATION.md) |

## 1. 边界

| 区块 | 职责 | 禁止 |
|------|------|------|
| **系统设置** | Founder、编排、Skill Hub 目录、MCP 全局 | ❌ 单角色 API Key |
| **角色设置** | 身份、Profile、模型槽、Skill 绑定 | ❌ 改 Founder 偏好 |
| 经营 Tab | 成本结果 | ❌ 改 Prompt |
| 工作室 | 单项目执行 | ❌ 装全局 Skill |

**Founder ≠ Agent Role** — Founder Profile 在系统设置；CEO/product/… 在角色设置。

---

## 2. 信息架构

### 2.1 顶栏

```
[ 系统设置 | 角色设置 ]                    Pulse · 6 角色 · 3 Skill
```

- 与经营 `fin-segment` 同组件语义
- 右侧可选状态 chips：已配 Key 角色数、Hub 活跃 Skill 数

### 2.2 系统设置

| Section | 上限 | 交互 |
|---------|------|------|
| Founder Profile | 摘要 1 行 + chips（待处理建议 N） | 展开 editor（现有 founder-doc-shell） |
| 编排与自动化 | **首屏 4 项** | Pulse 总开关、CEO 自动派活、Agency 观察、Proposal 日上限 |
| 编排高级 | 折叠 | interval、pauseWhileCeoThread 等 |
| Skill Hub | 列表 + 搜索 | 详情 drawer；导入；启用/停用 |
| MCP 连接 | 每连接 1 行 pill | 配置 Modal；测试 health |
| 渠道 | 2 pill 只读 | Phase C 可点 |

### 2.3 角色设置

| Section | 说明 |
|---------|------|
| **新增角色** | 顶栏 `[+ 新增角色]` → Modal（见 §4） |
| 角色列表 | 左栏或顶栏横 scroll；avatar + 名 + capability tags + Key 状态 |
| 角色详情 | 右栏；未选时 empty state |

**不预置** brand / 设计等 mock role — 用户自行创建。

---

## 3. 角色详情结构

```
┌─ 身份 ─────────────────────────────────────┐
│ 头像 [更换]  姓名  职位  部门               │
│ Charter（单行或多行）                       │
├─ Profile ──────────────────────────────────┤
│ Markdown 编辑器（同 Founder）              │
├─ 模型槽 ───────────────────────────────────┤
│ 文本对话   [provider] [model] [test]       │
│ 图像生成   [provider] [model] [test]       │
│ 视频生成   [provider] [model] [test]       │
│ Epic 4：MCP/image **stub**；槽位已可配 Key  │
├─ 技能 ─────────────────────────────────────┤
│ 从 Hub 勾选 enabledSkills[]               │
│ 可选：绑定 skillChain（Epic 5）            │
├─ 工具策略 ─────────────────────────────────┤
│ 有效 tools = skill 推导 ∪ 手动 allow/deny  │
├─ 预算 ─────────────────────────────────────┤
│ 月预算 · 链经营页本月成本                   │
└─ [保存] [测试连接] [停用角色] ─────────────┘
```

---

## 4. 新增角色 Modal

| 字段 | 必填 | 规则 |
|------|------|------|
| `id` | ✓ | `[a-z][a-z0-9_-]{1,24}` 创建后不可改 |
| `name` | ✓ | 显示名 |
| `title` | | 职位 |
| `department` | | 部门 |
| `capabilities` | ✓ | 多选：text / image / video / code |
| `dispatchable` | | 默认 true；CEO 可否派活 |
| `shortLabel` | | 概览缩写，默认 name 前两字 |

**创建后后端自动：**

- `roleRegistry` 追加条目（overview 默认坐标）
- `roles[]` 初始化 live 行
- `roleConfig[]` 空 models.text + 默认 budget
- `roleProfiles[id]` 空 document 或模板
- **不**自动绑 Skill；**不**复制其他 role 的 Key

---

## 5. 数据模型

### 5.1 systemSettings

```json
{
  "systemSettings": {
    "founderProfile": { "...": "同现 founderProfile" },
    "orchestration": { "...": "同 meta.runtimeSettings" },
    "channels": { "feishu": {}, "wechat": {} }
  }
}
```

### 5.2 roleRegistry

```json
{
  "roleRegistry": {
    "version": 2,
    "roles": [
      {
        "id": "ceo",
        "kind": "agent",
        "status": "active",
        "capabilities": ["text"],
        "department": "管理层",
        "shortLabel": "CEO",
        "dispatchable": true,
        "overview": { "x": 50, "y": 22 },
        "createdAt": "ISO8601"
      }
    ]
  }
}
```

### 5.3 roles[]（身份 · 可编辑）

```json
{
  "id": "brand",
  "name": "苏见",
  "title": "品牌设计 · AI",
  "department": "品牌部",
  "charter": "视觉、物料、品牌叙事",
  "avatar": "/api/v1/assets/avatars/brand.png",
  "workStatus": "idle",
  "load": { "current": 0, "max": 2 }
}
```

### 5.4 roleProfiles

```json
{
  "roleProfiles": {
    "brand": {
      "document": "# 品牌 Agent Profile\n...",
      "updatedAt": "ISO8601"
    }
  }
}
```

### 5.5 roleConfig（扩展）

```json
{
  "roleId": "brand",
  "monthlyBudget": 1200,
  "models": {
    "text":  { "model": "gpt-4o", "apiProvider": "OpenRouter", "apiBaseUrl": "..." },
    "image": { "model": "", "apiProvider": "", "enabled": false }
  },
  "enabledSkills": ["brand_moodboard_v1"],
  "toolPolicy": { "allow": [], "deny": [] },
  "rolePrompt": "兼容旧字段；优先 roleProfiles.document"
}
```

密钥仍在 SQLite `role_secrets`（按 roleId；MCP 独立 `mcp_secrets`）。

---

## 6. API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/settings/summary` | 系统+角色计数、健康摘要 |
| GET/PATCH | `/system/settings` | 编排等（founder 仍 `/founder/profile`） |
| GET | `/roles/registry` | 注册表 + 合并 identity 摘要 |
| POST | `/roles/registry` | **新增角色** |
| PATCH | `/roles/registry/{id}` | status、dispatchable、capabilities |
| PATCH | `/roles/{id}/identity` | name、title、avatar、charter |
| GET/PUT | `/roles/{id}/profile` | roleProfile document |
| GET/PUT | `/roles/config/{id}` | models、skills、toolPolicy |
| POST | `/roles/config/{id}/test` | 按 capability 测连接 |

---

## 7. 同步

```
sync_settings(dashboard)
  ├─ merge systemSettings.orchestration ← meta.runtimeSettings
  ├─ sync_role_registry(dashboard)
  │    ├─ bootstrap v1 五角色（若空）
  │    ├─ ensure roles[] / roleConfig[] / roleProfiles 条目齐全
  │    └─ strip 已删除 registry 的 orphan config
  └─ presentation.roles ← registry + live
```

**调用点：** `GET /dashboard` persist；`POST /roles/registry` 后；Skill 绑定变更后 invalidate runner cache（Epic 3）。

---

## 8. UI 交互防闪退

- `isSettingsUiInteractive()` — Modal、dropdown、editor focus、Skill drawer 打开时 Pulse 不重绘
- 状态 capture/restore — 选中 roleId、segment、open details

---

## 9. 废弃

- 设置页内「角色 API 配置」与 Founder/编排 **平铺三屏** 布局
- 前端硬编码 `ROLE_SHORT`、`KNOWN_AVATAR_ROLES`（改读 registry）
- 仅 `model` 单字段（迁移至 `models.text`）
