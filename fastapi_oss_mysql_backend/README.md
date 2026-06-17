# FastAPI + MySQL + OSS 后端工程模板

[![CI](https://github.com/lee/fastapi-oss-mysql-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/lee/fastapi-oss-mysql-backend/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> 一个生产就绪的 FastAPI 后端工程模板，集成 MySQL、阿里云 OSS、Redis、JWT 鉴权、限流、监控、链路追踪。

---

## ✨ 特性

- 🚀 **FastAPI 0.115+** + **Pydantic 2.x** + **SQLAlchemy 2.0 async**
- 🗄️ **MySQL** 异步驱动（aiomysql）+ **Alembic** 数据库迁移
- ☁️ **阿里云 OSS** 文件上传/下载封装
- 🔐 **JWT** 鉴权 + **bcrypt** 密码加密
- ⚡ **Redis** 缓存 + **slowapi** 限流
- 📊 **Prometheus** 指标监控 + **Sentry** 错误追踪
- 🔍 **OpenTelemetry** 链路追踪
- 🐳 **Docker** + **docker-compose** 一键部署
- 🧪 **pytest** 测试框架
- 🎨 **ruff** 格式化 + **mypy** 严格类型检查
- 📝 **loguru** 结构化日志

---

## 📁 目录结构

```
fastapi_oss_mysql_backend/
├── .github/workflows/         # GitHub Actions CI
├── alembic/                   # 数据库迁移
├── scripts/                   # 运维脚本
├── src/                       # 业务源码
│   ├── core/                  # 核心：配置/数据库/OSS/安全
│   ├── common/                # 通用：响应/中间件/工具
│   ├── db/models/             # ORM 模型
│   ├── api/v1/                # v1 接口路由
│   ├── schemas/               # Pydantic 模型
│   ├── crud/                  # 数据库操作层
│   ├── services/              # 业务逻辑层
│   └── main.py                # 入口
├── tests/                     # 测试用例
├── pyproject.toml             # uv 依赖配置
├── Dockerfile                 # 多阶段构建
└── docker-compose.yml         # 一键启动
```

---

## 🚀 快速开始

### 1. 环境准备

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 包管理器
- MySQL 8.0+
- Redis 7.0+（可选）
- 阿里云 OSS 账号（可选）

### 2. 安装 uv

```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 克隆并安装依赖

```bash
git clone https://github.com/lee/fastapi-oss-mysql_backend.git
cd fastapi-oss-mysql-backend

# 安装依赖（含开发依赖）
uv sync --extra dev

# 复制环境变量
cp env.example .env
# 编辑 .env 填入真实配置
```

### 4. 启动 MySQL（推荐 Docker）

```bash
docker-compose up -d mysql redis
```

### 5. 初始化数据库

```bash
# 创建初始迁移（首次）
uv run alembic revision --autogenerate -m "init schema"

# 执行迁移
uv run alembic upgrade head

# 初始化管理员/字典数据
uv run python scripts/init_data.py
```

### 6. 启动服务

```bash
# 开发模式（热重载）
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uv run python src/main.py
```

访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 Swagger 文档。

---

## 🐳 Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f api

# 进入容器
docker-compose exec api bash
```

---

## 🛠️ 常用命令

```bash
make help            # 查看所有命令
make install         # 安装依赖
make run             # 启动开发服务
make test            # 运行测试
make lint            # 代码检查
make format          # 代码格式化
make migrate         # 执行数据库迁移
make migration msg   # 创建新迁移（msg=迁移说明）
make docker-up       # 启动 Docker 服务
make docker-down     # 停止 Docker 服务
```

---

## 📚 接口文档

启动服务后访问：

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Prometheus 指标: <http://localhost:8000/metrics>
- 健康检查: <http://localhost:8000/api/v1/health>

---

## 🏗️ 架构分层

```
HTTP Request
    ↓
Middleware（CORS / Logging / RateLimit）
    ↓
API Router（依赖注入 / 鉴权）
    ↓
Schemas（Pydantic 校验）
    ↓
Services（业务编排 / 事务）
    ↓
CRUD（纯 ORM 操作）
    ↓
MySQL / Redis / OSS
```

---

## 🔒 安全说明

- 生产环境务必修改 `SECRET_KEY`（使用 `openssl rand -hex 32` 生成）
- 关闭 `--reload`、开启 HTTPS
- 配置 CORS 白名单（不要用 `allow_origins=["*"]`）
- 启用 Sentry 监控生产异常
- 数据库密码使用 Vault / AWS Secrets Manager 管理

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [阿里云 OSS](https://help.aliyun.com/product/31815.html)
