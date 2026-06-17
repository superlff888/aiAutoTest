#!/usr/bin/env bash
# ============================================
# 启动 FastAPI 服务脚本
# ============================================
set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 启动 FastAPI 服务...${NC}"

# 检查 .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env 文件不存在，请先复制 env.example:${NC}"
    echo "   cp env.example .env"
    exit 1
fi

# 选择启动模式
MODE=${1:-dev}

if [ "$MODE" = "prod" ]; then
    echo -e "${YELLOW}📦 生产模式启动${NC}"
    uv run uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 4 \
        --proxy-headers \
        --forwarded-allow-ips='*'
else
    echo -e "${YELLOW}🔧 开发模式启动（热重载）${NC}"
    uv run uvicorn src.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info
fi
