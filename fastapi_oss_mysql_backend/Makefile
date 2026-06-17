.PHONY: help install run test lint format migrate migration docker-up docker-down clean

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

help: ## 显示帮助信息
	@echo "$(BLUE)📚 可用命令：$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

install: ## 安装依赖
	uv sync --extra dev
	@echo "$(GREEN)✅ 依赖安装完成$(NC)"

run: ## 启动开发服务（热重载）
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## 启动生产服务
	uv run python src/main.py

test: ## 运行测试
	uv run pytest -v --cov=src --cov-report=term-missing

test-fast: ## 运行快速测试（跳过慢测试）
	uv run pytest -v -m "not slow" --cov=src

lint: ## 代码检查
	uv run ruff check src tests
	uv run mypy src

format: ## 代码格式化
	uv run ruff format src tests
	uv run ruff check --fix src tests

migrate: ## 执行数据库迁移
	uv run alembic upgrade head

migration: ## 创建新迁移（用法：make migration msg="添加用户表"）
	uv run alembic revision --autogenerate -m "$(msg)"

rollback: ## 回滚一次迁移
	uv run alembic downgrade -1

init-data: ## 初始化数据
	uv run python scripts/init_data.py

docker-up: ## 启动 Docker 服务
	docker-compose up -d --build

docker-down: ## 停止 Docker 服务
	docker-compose down

docker-logs: ## 查看 Docker 日志
	docker-compose logs -f api

pre-commit: ## 安装并运行 pre-commit
	uv run pre-commit install
	uv run pre-commit run --all-files

clean: ## 清理缓存文件
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null
	rm -rf htmlcov .coverage
	@echo "$(GREEN)✅ 清理完成$(NC)"
