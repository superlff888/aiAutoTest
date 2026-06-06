# RPA 数据采集校验 — GitHub Actions 定时执行技术方案

> 方案选型：**GitHub Actions（云端定时） + Ubuntu Runner（7×24 在线）**
> 编写日期：2026-06-06

---

## 1. 总体架构

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions（云端，7×24 在线）                         │
│  每天 08:30 / 17:10（北京时间）自动触发                     │
│  支持手动触发（Actions 面板 Run workflow）                  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Ubuntu-latest Runner（2C/7G，免费 2000 min/月）           │
│  1. Checkout 代码                                         │
│  2. uv sync 安装依赖                                      │
│  3. 执行 run_check.py                                     │
└────────┬──────────────────────┬──────────────────────────┘
         │                      │
         ▼                      ▼
┌────────────────┐   ┌────────────────────────────────────┐
│ MySQL（生产库） │   │ 飞书 Webhook → 交互消息卡片          │
│ 需公网可达      │   │ 或本地 Windows 兜底                  │
└────────────────┘   └────────────────────────────────────┘
```

### 解耦设计原则

| 原则 | 实现方式 |
|------|----------|
| **零成本** | GitHub Actions 免费额度（public repo 无限，private repo 2000 min/月） |
| **免运维** | 无需本地机器在线，GitHub 基础设施自动运行 |
| **安全存储** | 敏感信息存在 GitHub Secrets，不提交代码 |
| **可追溯** | 每次执行记录、日志、失败详情都在 Actions 面板可见 |
| **可回滚** | 每次执行基于特定 commit，出问题可追溯历史版本 |

---

## 2. 触发时间配置

北京时间 = UTC+8，GitHub Actions cron 使用 UTC 时间：

| 北京时间 | UTC 时间 | cron 表达式 |
|----------|----------|-------------|
| 08:30 | 00:30 | `30 0 * * *` |
| 17:10 | 09:10 | `10 9 * * *` |

Workflow 文件 `.github/workflows/rpa-check.yml` 中配置：

```yaml
on:
  schedule:
    - cron: '30 0 * * *'   # 北京 08:30
    - cron: '10 9 * * *'   # 北京 17:10
  workflow_dispatch:       # 手动触发支持
```

---

## 3. GitHub Secrets 配置

### 3.1 配置路径

仓库地址：`https://github.com/superlff888/aiAutoTest/settings/secrets/actions`

### 3.2 所需 Secret 列表

| Secret 名称 | 值示例 | 必填 | 说明 |
|-------------|--------|------|------|
| `FEISHU_WEBHOOK_URL` | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` | ✅ | 飞书自定义机器人 Webhook |
| `FEISHU_WEBHOOK_SECRET` | `SECxxxxxxxx` | ❌ | 签名密钥（如启用签名校验） |
| `FEISHU_APP_ID` | `cli_xxxxxxxx` | ❌ | 飞书应用 ID（wiki 更新用） |
| `FEISHU_APP_SECRET` | `xxxxxxxx` | ❌ | 飞书应用密钥 |
| `PROD_MYSQL_HOST` | `x.x.x.x` 或 `domain.com` | ✅ | 生产数据库地址（需公网可达） |
| `PROD_MYSQL_PORT` | `3306` | ✅ | 生产数据库端口 |
| `PROD_MYSQL_USER` | `xxx` | ✅ | 生产数据库用户名 |
| `PROD_MYSQL_PASSWORD` | `xxx` | ✅ | 生产数据库密码 |
| `PROD_MYSQL_DATABASE` | `xxx` | ✅ | 生产数据库名 |
| `TEST_MYSQL_HOST` | `x.x.x.x` | ❌ | 测试数据库地址（可选） |
| `TEST_MYSQL_PORT` | `3306` | ❌ | 测试数据库端口（可选） |
| `TEST_MYSQL_USER` | `xxx` | ❌ | 测试数据库用户名（可选） |
| `TEST_MYSQL_PASSWORD` | `xxx` | ❌ | 测试数据库密码（可选） |
| `TEST_MYSQL_DATABASE` | `xxx` | ❌ | 测试数据库名（可选） |

### 3.3 Secret 命名规范

遵循项目现有的 `db_executor.py` 命名约定：
- `{ENV}_MYSQL_HOST`
- `{ENV}_MYSQL_PORT`
- `{ENV}_MYSQL_USER`
- `{ENV}_MYSQL_PASSWORD`
- `{ENV}_MYSQL_DATABASE`

支持的环境：`PROD`（生产）、`TEST`（测试）

---

## 4. Workflow 文件详解

### 4.1 目录结构

```
.github/
└── workflows/
    └── rpa-check.yml      ← 工作流定义（本文档所述方案）
```

### 4.2 执行步骤

```yaml
步骤 1: Checkout code
  └→ 拉取仓库代码到 Runner

步骤 2: Install uv
  └→ 安装 uv 包管理器（astral-sh/setup-uv@v4）

步骤 3: Install dependencies
  └→ uv sync --frozen（从 uv.lock 精确安装依赖）

步骤 4: Run RPA check
  └→ uv run python .claude/skills/prod-rpa-checker/run_check.py
     ├── --connection prod（默认）
     └── 环境变量自动注入（通过 env: 映射 Secrets）

步骤 5: Upload report artifact（always）
  └→ 上传 .md 报告文件，保留 7 天，可下载

步骤 6: Upload logs（always）
  └→ 上传 .log 日志文件，保留 7 天，可下载
```

### 4.3 手动触发参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `connection` | string | `prod` | 数据库连接（prod/test） |
| `notify` | choice | `true` | 是否发送飞书通知（true/false） |

---

## 5. 依赖管理

### 5.1 新增依赖

`pyproject.toml` 中新增：

```toml
[project]
dependencies = [
    # ... 原有依赖
    "pyyaml>=6.0.2",        # ← 新增（config.yaml 解析）
    "requests>=2.32.5",     # ← 新增（飞书 Webhook 推送）
]
```

### 5.2 依赖列表

| 依赖 | 用途 | 状态 |
|------|------|------|
| `pymysql` | MySQL 数据库连接 | ✅ 已有 |
| `python-dotenv` | .env 文件加载 | ✅ 已有 |
| `pyyaml` | config.yaml 解析 | ✅ 新增 |
| `requests` | 飞书 Webhook HTTP 请求 | ✅ 新增 |
| `rich` | 终端输出格式化 | ✅ 已有 |

### 5.3 依赖同步

```bash
# 修改 pyproject.toml 后执行
uv lock          # 更新 uv.lock
uv sync          # 安装新依赖
```

---

## 6. 网络问题与解决方案

### 6.1 问题描述

GitHub Actions Runner 运行在美国的云服务器上，IP 地址不固定（属于 `actions-runner` IP 池）。如果 MySQL 数据库：

- **内网地址**（如 `192.168.x.x`、`10.x.x.x`）→ ❌ 无法访问
- **有公网 IP 但防火墙限制来源** → ❌ GitHub IP 可能被拦截
- **有公网 IP 且允许所有来源** → ✅ 可以直接访问

### 6.2 方案 A：数据库公网暴露（最简单）

**适用场景**：数据库有公网 IP，或可通过路由器端口映射

1. 在路由器/防火墙上做端口映射：
   ```
   公网IP:13306 → 内网数据库:3306
   ```
2. GitHub Secrets 中配置：
   ```
   PROD_MYSQL_HOST = <公网IP>
   PROD_MYSQL_PORT = 13306
   ```

**安全建议**：
- ✅ 使用非标准端口（不要 3306）
- ✅ 数据库密码使用强密码
- ✅ MySQL 配置 `bind-address = 0.0.0.0` 但限制用户来源 IP
- ✅ 创建专用只读用户，仅开放查询权限

**MySQL 用户权限配置**：
```sql
-- 创建只读用户，仅限查询
CREATE USER 'rpa_checker'@'%' IDENTIFIED BY 'StrongP@ssw0rd!';
GRANT SELECT ON <database>.* TO 'rpa_checker'@'%';
FLUSH PRIVILEGES;
```

### 6.3 方案 B：Cloudflare Tunnel（推荐，安全免费）

**适用场景**：数据库在内网，但需要安全暴露到公网

```
GitHub Actions → Cloudflare Edge → Cloudflare Tunnel → 本地数据库
```

**部署步骤**：

1. 在数据库所在机器安装 `cloudflared`：
   ```bash
   # Linux
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
   chmod +x /usr/local/bin/cloudflared

   # Windows
   winget install cloudflared
   ```

2. 创建 Tunnel 并配置 TCP 转发：
   ```bash
   # 登录 Cloudflare
   cloudflared tunnel login

   # 创建 Tunnel
   cloudflared tunnel create rpa-mysql

   # 配置路由（cloudflared 配置文件）
   #  ~/.cloudflared/config.yml:
   tunnel: <tunnel-id>
   credentials-file: ~/.cloudflared/<tunnel-id>.json
   ingress:
     - hostname: mysql.yourdomain.com
       service: tcp://localhost:3306
     - service: http_status:404
   ```

3. 启动 Tunnel：
   ```bash
   cloudflared tunnel run rpa-mysql
   ```

4. 在 Cloudflare Dashboard 配置 DNS：
   ```
   mysql.yourdomain.com → CNAME → <tunnel-id>.cfargotunnel.com
   ```
   启用 Cloudflare Tunnel（非 HTTP），支持 TCP 透传。

5. GitHub Secrets 中配置：
   ```
   PROD_MYSQL_HOST = mysql.yourdomain.com
   PROD_MYSQL_PORT = 443  # Cloudflare Tunnel 默认端口
   ```

**优点**：
- ✅ 无需开放端口到公网
- ✅ 免费（Cloudflare Zero Trust 免费版）
- ✅ 加密传输
- ✅ 来源 IP 不暴露数据库真实 IP

### 6.4 方案 C：Self-hosted Runner（内网直连）

**适用场景**：有本地服务器/电脑可长期运行

在本地机器注册 GitHub Self-hosted Runner：

```bash
# 仓库 Settings → Actions → Runners → New self-hosted runner
# 按提示下载并配置

# 注册为 Windows 服务
.\run.cmd --runasservice
```

**优点**：
- ✅ 直接访问内网数据库
- ✅ 不消耗免费额度
- ✅ 速度更快（本地网络）

**缺点**：
- ❌ 依赖本地机器在线（和 Windows 任务计划一样的问题）
- ❌ 需要维护 Runner 状态

### 6.5 方案 D：混合模式（GitHub CI + Windows 生产）

**适用场景**：数据库纯内网，不想折腾网络

| 用途 | 执行环境 | 频率 |
|------|----------|------|
| **代码 CI** | GitHub Actions | 每次 push 时 |
| **定时校验** | Windows 任务计划 | 每天 08:30 / 17:10 |

Workflow 改为仅在 push 时触发，验证代码正确性：

```yaml
on:
  push:
    paths:
      - '.claude/skills/prod-rpa-checker/**'
      - '.github/workflows/rpa-check.yml'
  pull_request:
    paths:
      - '.claude/skills/prod-rpa-checker/**'
```

---

## 7. 执行流程

```
每次触发（定时 / 手动）
    │
    ▼
┌─ Step 1: Checkout
│   └→ 拉取仓库代码到 Runner（含技能脚本、SQL、配置）
│
    ▼
┌─ Step 2: uv sync
│   └→ 安装所有依赖（pymysql、requests、pyyaml 等）
│
    ▼
┌─ Step 3: run_check.py
│   │
│   ├─ 加载环境变量（GitHub Secrets → 进程环境变量）
│   ├─ 加载 config.yaml（wiki 链接、通知策略）
│   ├─ 连接 MySQL（通过 Secrets 中的配置）
│   │
│   ├─ 并行查询 13 个交易中心数据
│   │   ├── 最新数据时间验证
│   │   ├── 日期连续性验证（近10天）
│   │   ├── 数据量合理性校验
│   │   └── 明细与总计差异检查
│   │
│   ├─ 生成 Markdown 报告 → output/ 目录
│   │
│   ├─ 推送飞书通知（Webhook → 交互卡片）
│   │   ├── 有失败 → 红色卡片
│   │   └── 全通过 → 绿色卡片
│   │
│   └─ 更新 Wiki 文档（可选，需 App ID/Secret）
│
    ▼
┌─ Step 4: Upload artifacts
│   └→ 报告 + 日志上传到 GitHub，保留 7 天
│
    ▼
  完成 → Actions 面板显示 ✅ 或 ❌
```

---

## 8. 监控与告警

### 8.1 GitHub Actions 原生通知

| 事件 | 通知方式 | 配置 |
|------|----------|------|
| Workflow 失败 | GitHub 邮件 / 手机推送 | Settings → Notifications |
| Workflow 成功 | 可选通知 | 同上 |

### 8.2 失败告警升级

如果 Workflow 执行失败（非数据校验失败，而是脚本/网络错误），可以添加额外告警：

```yaml
# 在 workflow 中添加
    - name: Notify on failure
      if: failure()
      run: |
        curl -X POST "$FEISHU_WEBHOOK_URL" \
          -H "Content-Type: application/json" \
          -d '{
            "msg_type": "text",
            "content": {
              "text": "⚠️ RPA 校验任务执行失败！\nGitHub Actions: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
            }
          }'
```

### 8.3 查看执行历史

| 入口 | 地址 |
|------|------|
| Actions 列表 | `https://github.com/superlff888/aiAutoTest/actions` |
| 具体执行日志 | Actions → RPA Data Check → 某次 Run → 展开 `Run RPA check` |
| 下载报告 | Actions → 某次 Run → Artifacts 区域下载 |

---

## 9. 成本分析

| 项目 | 用量 | 费用 |
|------|------|------|
| GitHub Actions 分钟数 | ~3 min/次 × 2次/天 = 180 min/月 | 免费（private repo 2000 min/月） |
| 存储空间 | artifacts 7天保留，每次 ~50KB | 免费（500MB 额度） |
| 数据库连接 | 每天 2 次，每次 ~100 查询 | 无额外费用 |
| 飞书 Webhook | 每天 2 条消息 | 免费 |

**总成本：¥0/月**（假设数据库已公网可达）

---

## 10. 与 Windows 任务计划对比

| 维度 | GitHub Actions | Windows 任务计划 |
|------|----------------|------------------|
| 💰 成本 | 免费 | 免费（但需机器在线） |
| 🟢 在线 | 7×24 云端 | 依赖本地机器 |
| 😴 睡眠/关机 | 不影响 | 不执行（除非 WakeToRun） |
| 🌐 网络要求 | MySQL 需公网可达 | 内网即可 |
| 📊 可追溯 | Actions 面板完整记录 | 需本地翻日志 |
| 🔒 安全 | Secrets 加密存储 | .env 文件本地存储 |
| 📝 改造成本 | 需配置 Secrets + 网络 | 已部署完成 |
| ⚡ 执行速度 | ~30s（含环境初始化） | ~33s（无初始化开销） |

---

## 11. 后续扩展

| 扩展方向 | 说明 |
|----------|------|
| **Slack/DingTalk 通知** | 多渠道推送，不局限于飞书 |
| **数据趋势图** | 在 Workflow 中生成图表，上传到 artifact |
| **多环境对比** | 同时跑 prod + test，对比差异 |
| **PR 检查门禁** | 修改技能代码时自动跑一次校验，防止破坏 |
| **执行时间优化** | 缓存 uv 依赖，减少安装时间（从 10s → 3s） |

---

## 12. 实施检查清单

- [ ] 创建 `.github/workflows/rpa-check.yml` ✅ 已完成
- [ ] `pyproject.toml` 新增 `pyyaml`、`requests` ✅ 已完成
- [ ] `uv lock` 更新依赖锁文件 ✅ 已完成
- [ ] `git push` 推送代码到 GitHub
- [ ] 在 GitHub Settings → Secrets 添加所有 Secret
- [ ] 确认 MySQL 公网可达（或选择网络方案）
- [ ] 手动触发一次 Workflow 验证
- [ ] 检查飞书是否收到通知
- [ ] 确认定时触发生效（次日检查）
