# OpenClaw ↔ OPC Studio Bridge

将 **OpenClaw Gateway** 收到的微信消息转发到 OPC Studio CEO。

> **重要：** 微信绑定本身走官方 ClawBot 流程（`npx @tencent-weixin/openclaw-weixin-cli install` → 终端/微信扫码），**不是**在 OPC 设置页填 URL。本 Bridge 是第 3 步：让已绑定的微信消息进入 OPC CEO。

## 正确流程（与官方一致）

1. **终端扫码绑定微信**（OpenClaw ↔ 微信）
   ```bash
   npx -y @tencent-weixin/openclaw-weixin-cli@latest install
   ```
   或：`./scripts/wechat-clawbot-setup.sh`

2. **（可选）手机微信**：我 → 设置 → 插件 → ClawBot → 扫码

3. **启动 OPC Bridge**（微信 → OPC CEO）
   ```bash
   cd bridge/openclaw-opc && npm install && npm start
   ```

## 架构

```
微信 ClawBot → OpenClaw Gateway (:9200)
                    ↓ getupdates（本 Bridge 轮询）
              POST /api/v1/channels/inbound
                    ↓ CEO 编排
              POST /openclaw/sendmessage（OPC 自动出站）
                    ↓
              微信用户收到 CEO 回复
```

## 前置条件

1. OPC Studio 已启动：`./start.sh`
2. OpenClaw Gateway 已启用 **openclaw** 通道（参考 [wechat-clawbot-gateway](https://github.com/fooling/wechat-clawbot-gateway) 或官方 ClawBot CLI）
3. 公网隧道（Bridge 与 OPC 同机时可省略）：Cloudflare Tunnel / ngrok

## 快速开始

```bash
cd bridge/openclaw-opc
cp config.example.json config.json
# 编辑 config.json：opcInboundUrl、openclawGatewayUrl、token

npm install   # 无依赖，仅保留 package 脚本
npm start
```

## config.json

| 字段 | 说明 |
|------|------|
| `opcInboundUrl` | OPC 入站，默认 `http://127.0.0.1:8765/api/v1/channels/inbound` |
| `opcChannelToken` | 与 OPC 环境变量 `OPC_CHANNEL_SECRET` 一致（可选） |
| `openclawGatewayUrl` | Gateway OpenClaw 服务地址，如 `http://127.0.0.1:9200` |
| `openclawToken` | Gateway `channels.openclaw.token` |
| `defaultSenderName` | 写入 CEO 线程的发送者显示名 |

## Gateway 配置示例（wechat-clawbot-gateway）

```yaml
channels:
  openclaw:
    enabled: true
    port: 9200
    token: "my-agent-token"
```

## OPC 设置页

**系统设置 → 渠道 → 微信** 填写：

- **Gateway URL**：`http://127.0.0.1:9200`
- **Gateway Token**：与 Gateway 一致
- **出站模式**：OpenClaw（默认）或 Webhook（`channels.webhook` 端口 9100）

点击 **测试连接** 验证 Gateway 可达；CEO 回复后会自动调用 `sendmessage` 推回微信。

## 安全

- 生产环境务必设置 `OPC_CHANNEL_SECRET`，Bridge `config.json` 填相同 token
- Gateway token 与 OPC 设置页分槽保存，GET API 返回打码

## 故障排查

| 现象 | 检查 |
|------|------|
| Bridge 连不上 Gateway | `curl -X POST http://127.0.0.1:9200/openclaw/getupdates -H "Authorization: Bearer TOKEN" -d '{}'` |
| OPC 401 | `OPC_CHANNEL_SECRET` 与 Bridge token 不一致 |
| 微信无回复 | OPC 设置页 Gateway URL/Token；查看后端日志 `WeChat outbound` |
| 飞书 | 尚未实现，请先用微信 ClawBot 路径 |
