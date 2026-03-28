# Cloudflare Workers 部署指南

## 概述

本指南介绍如何从 GitHub 自动部署到 Cloudflare Workers，无需本地安装任何工具。

## 项目结构

```
AMDCHAT/
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions 自动部署配置
├── src/
│   └── worker.js           # Cloudflare Workers 主代码
├── wrangler.toml           # Cloudflare 配置
├── package.json            # npm 配置
└── ...                     # 其他原有文件
```

## 部署步骤

### 第一步：准备 Cloudflare 账户

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 获取 **Account ID**：
   - 在右侧边栏找到 "Account ID" 并复制

3. 创建 **API Token**：
   - 点击右上角头像 → "My Profile"
   - 选择 "API Tokens" 标签
   - 点击 "Create Token"
   - 选择 "Custom token" 模板
   - 配置如下：
     - Token name: `GitHub Actions Deploy`
     - Permissions:
       - `Cloudflare Workers:Edit`
       - `Zone:Read` (如果需要自定义域名)
     - Account Resources: Include - Your Account
   - 点击 "Continue to summary" → "Create Token"
   - **立即复制 Token**（只显示一次）

### 第二步：创建 KV Namespace

1. 在 Cloudflare Dashboard 中：
   - 点击左侧菜单 "Workers & Pages"
   - 点击 "KV"
   - 点击 "Create a namespace"
   - 名称输入: `AMDCHAT_KV`
   - 点击 "Add"

2. 复制 KV Namespace ID：
   - 点击刚创建的 namespace
   - 复制 "Namespace ID"

### 第三步：配置 GitHub Secrets

1. 打开你的 GitHub 仓库
2. 点击 "Settings" → "Secrets and variables" → "Actions"
3. 点击 "New repository secret" 添加以下 secrets：

| Secret Name | Value |
|------------|-------|
| `CLOUDFLARE_API_TOKEN` | 第一步创建的 API Token |
| `CLOUDFLARE_ACCOUNT_ID` | 第一步获取的 Account ID |
| `BOT_TOKEN` | Telegram Bot Token (例如: 123456789:ABCdef...) |

### 第四步：更新 wrangler.toml

编辑 `wrangler.toml` 文件，将 `YOUR_KV_NAMESPACE_ID` 替换为实际的 KV Namespace ID：

```toml
name = "amdchat-bot"
main = "src/worker.js"
compatibility_date = "2024-01-01"

[[kv_namespaces]]
binding = "KV"
id = "你的实际KV_NAMESPACE_ID"  # ← 替换这里
```

### 第五步：推送代码

将更改推送到 GitHub：

```bash
git add .
git commit -m "Add Cloudflare Workers deployment"
git push origin main
```

推送后，GitHub Actions 会自动部署到 Cloudflare Workers。

### 第六步：查看部署状态

1. 在 GitHub 仓库中点击 "Actions" 标签
2. 查看 "Deploy to Cloudflare Workers" 工作流
3. 等待显示绿色 ✓ (成功)

### 第七步：设置 Telegram Webhook

部署成功后，获取 Workers URL 并设置 webhook：

1. 在 Cloudflare Dashboard → Workers & Pages → amdchat-bot
2. 复制 URL (例如: `https://amdchat-bot.your-account.workers.dev`)

3. 在浏览器中访问以下 URL 设置 webhook：
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://amdchat-bot.your-account.workers.dev
```

成功响应：
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

## 功能测试

将 bot 添加到 Telegram 群组后，测试以下功能：

- `/start` - 开始消息
- `/help` - 帮助信息
- `/mystats` - 我的消息数量
- `/rank` - 聊天排名 Top 10
- `/attend` 或 `ㅊㅊ`, `출첵`, `출석체크` - 出勤检查
- `/attendrank` - 出勤排名 Top 10

## 重新部署

以后每次推送代码到 main 分支，GitHub Actions 会自动重新部署。

或者手动触发部署：
1. GitHub 仓库 → Actions
2. 选择 "Deploy to Cloudflare Workers"
3. 点击 "Run workflow"

## 故障排除

### 部署失败
1. 检查 GitHub Secrets 是否正确设置
2. 查看 Actions 日志获取详细错误信息

### Bot 不响应
1. 检查 webhook 是否设置正确：
   ```
   https://api.telegram.org/bot<TOKEN>/getWebhookInfo
   ```
2. 检查 Cloudflare Workers 日志：
   - Dashboard → Workers & Pages → amdchat-bot → Logs

### KV 存储问题
1. 确认 KV Namespace ID 在 wrangler.toml 中正确配置
2. 确认 GitHub Secrets 中的 CLOUDFLARE_API_TOKEN 有 Workers KV 权限

## 免费额度限制

Cloudflare Workers 免费计划：
- 每天 100,000 请求
- KV 读取：每天 100,000 次
- KV 写入：每天 1,000 次
- KV 存储：1GB

对于小型 Telegram 群组完全足够。
