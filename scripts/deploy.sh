#!/usr/bin/env bash
# ── VPS 自动化部署脚本 ─────────────────────────────────────────
# 用于 GitHub Actions CI/CD 流水线 或 手动 SSH 执行
# 仓库: github.com/WUIR/flask-user
set -euo pipefail

APP_DIR="/opt/flask-user"
COMPOSE_FILE="${APP_DIR}/docker/docker-compose.yml"
ENV_FILE="${APP_DIR}/.env"
IMAGE_NAME="ghcr.io/WUIR/flask-user:latest"

echo "=========================================="
echo " Flask 用户系统 - 自动化部署"
echo "=========================================="

# ── 1. 环境检查 ──────────────────────────────────────────────
echo ""
echo "==> [1/6] 检查系统依赖..."

if ! command -v docker &>/dev/null; then
    echo "    -> 安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker "$(whoami)"
    echo "    -> 请重新登录后再次运行脚本"
    exit 0
fi

if ! docker compose version &>/dev/null; then
    echo "    -> 安装 Docker Compose 插件..."
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p "$DOCKER_CONFIG/cli-plugins"
    PLUGIN_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)"
    curl -sSL "$PLUGIN_URL" -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
    chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
fi
echo "    -> Docker: $(docker --version)"
echo "    -> Compose: $(docker compose version)"

# ── 2. 首次安装：克隆代码 + 创建配置 ─────────────────────────
echo ""
echo "==> [2/6] 检查项目目录..."

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "    -> 首次部署，创建项目目录..."
    mkdir -p "$APP_DIR/docker" "$APP_DIR/nginx/ssl"

    # 下载配置文件
    GITHUB_RAW="https://raw.githubusercontent.com/WUIR/flask-user/main"
    curl -sSL "$GITHUB_RAW/docker/docker-compose.yml" -o "$COMPOSE_FILE"
    curl -sSL "$GITHUB_RAW/nginx/app.conf" -o "$APP_DIR/nginx/app.conf"

    # 如果没有 .env，创建默认配置
    if [ ! -f "$ENV_FILE" ]; then
        echo "    -> 生成 .env 配置..."
        cat > "$ENV_FILE" <<- ENVEOF
			SECRET_KEY=$(openssl rand -hex 32)
			JWT_SECRET_KEY=$(openssl rand -hex 32)
			POSTGRES_PASSWORD=$(openssl rand -hex 16)
			CORS_ORIGINS=https://your-domain.com
			ENVEOF
        echo "    -> 请编辑 $ENV_FILE 设置你的域名"
    fi
else
    echo "    -> 项目已存在，跳过初始化"
fi

# 加载环境变量
set -a; source "$ENV_FILE"; set +a

# ── 3. 拉取最新镜像 ─────────────────────────────────────────
echo ""
echo "==> [3/6] 拉取最新 Docker 镜像..."
echo "    -> 镜像: $IMAGE_NAME"
docker pull "$IMAGE_NAME" 2>/dev/null || echo "    -> 镜像未在 GHCR 找到，尝试本地构建"
cd "$APP_DIR"

# ── 4. 数据库迁移 ────────────────────────────────────────────
echo ""
echo "==> [4/6] 执行数据库迁移..."
docker compose -f "$COMPOSE_FILE" run --rm app flask db upgrade 2>/dev/null || \
    echo "    -> 迁移跳过（首次部署时需手动执行）"

# ── 5. 重启服务 ─────────────────────────────────────────────
echo ""
echo "==> [5/6] 重启服务..."
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" up -d

# ── 6. 健康检查 ─────────────────────────────────────────────
echo ""
echo "==> [6/6] 健康检查..."
sleep 5
HEALTH_URL="http://localhost:8000/api/v1/health"
if curl -sf "$HEALTH_URL" | grep -q "ok"; then
    echo ""
    echo "  ✅  部署成功！"
    echo "  🌐  https://your-domain.com/api/v1/health"
else
    echo ""
    echo "  ❌  健康检查失败，查看日志："
    echo "  docker compose -f $COMPOSE_FILE logs app"
    exit 1
fi
