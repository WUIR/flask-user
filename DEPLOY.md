# Flask 用户系统 — VPS 部署指南

> 适用于 Ubuntu 22.04 / Debian 12 VPS 服务器

## 前置准备

- 一台公网 VPS（最低配置 1C1G 即可）
- 一个域名（可选，不用域名可用 IP 访问 HTTP）
- GitHub 账号 `WUIR`

---

## 步骤一：GitHub 仓库配置

### 1.1 创建仓库

在 GitHub 上创建仓库 `flask-user`（Public 或 Private 均可），然后推送代码：

```bash
# 本地（本机 PowerShell）
cd w:/A-PythonProjects/Flask-user
git init
git add .
git commit -m "feat: complete flask user system"
git branch -M main
git remote add origin https://github.com/WUIR/flask-user.git
git push -u origin main
```

### 1.2 配置 GitHub Secrets

进入仓库 → **Settings → Secrets and variables → Actions**，添加以下密钥：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `VPS_HOST` | VPS 的公网 IP 或域名 | `123.45.67.89` |
| `VPS_USER` | SSH 用户名 | `root` 或 `ubuntu` |
| `VPS_SSH_KEY` | SSH 私钥（`cat ~/.ssh/id_rsa` 的内容） | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### 1.3 推送触发 CI/CD

推送 `main` 分支后，GitHub Actions 会自动：
1. **test** — 运行 pytest，要求覆盖率 100%
2. **build** — 构建 Docker 镜像并推送到 `ghcr.io/WUIR/flask-user:latest`
3. **deploy** — SSH 到 VPS 拉取镜像并重启服务

---

## 步骤二：VPS 初始化

SSH 登录到你的 VPS，运行以下命令：

### 2.1 安装 Docker

```bash
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 退出 SSH 重新登录使组生效
exit
```

### 2.2 创建项目目录与配置文件

```bash
ssh root@<VPS_IP>

# 创建目录
mkdir -p /opt/flask-user/{docker,nginx,nginx/ssl}

# 下载 docker-compose.yml
curl -o /opt/flask-user/docker/docker-compose.yml \
  https://raw.githubusercontent.com/WUIR/flask-user/main/docker/docker-compose.yml

# 下载 nginx 配置
curl -o /opt/flask-user/nginx/app.conf \
  https://raw.githubusercontent.com/WUIR/flask-user/main/nginx/app.conf
```

### 2.3 配置环境变量

```bash
cat > /opt/flask-user/.env << 'EOF'
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
CORS_ORIGINS=https://your-domain.com
EOF
```

### 2.4 配置 SSL 证书

**方式 A：Let's Encrypt（推荐，自动续期）**

```bash
# 先临时启动 Nginx 用 HTTP 验证
docker run -d --rm -p 80:80 nginx:alpine
apt-get install -y certbot
certbot certonly --standalone -d your-domain.com

# 复制证书
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/flask-user/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/flask-user/nginx/ssl/

# 设置自动续期
echo "0 3 * * * root docker run --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot renew --quiet && docker exec flask-user-nginx-1 nginx -s reload" > /etc/cron.d/certbot-renew
```

**方式 B：自签名证书（测试用）**

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /opt/flask-user/nginx/ssl/privkey.pem \
  -out /opt/flask-user/nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

### 2.5 验证配置文件

用 `docker compose config` 检查配置是否正确（先无需运行）：

```bash
docker compose -f /opt/flask-user/docker/docker-compose.yml config --quiet
```

---

## 步骤三：首次启动

### 3.1 拉取镜像并启动

```bash
cd /opt/flask-user
docker compose -f docker/docker-compose.yml pull
docker compose -f docker/docker-compose.yml up -d
```

### 3.2 运行数据库迁移

```bash
docker compose -f docker/docker-compose.yml exec app flask db upgrade
```

### 3.3 健康检查

```bash
curl -s http://localhost:8000/api/v1/health
# 预期返回: {"status": "ok"}
```

通过 Nginx 访问：

```bash
# HTTP (会 301 跳转到 HTTPS)
curl -s http://your-domain.com/api/v1/health

# HTTPS
curl -s https://your-domain.com/api/v1/health
```

### 3.4 验证 API

```bash
# 注册
curl -s -X POST https://your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"Admin123456"}'

# 登录
curl -s -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"Admin123456"}'
```

---

## 步骤四：后续维护

### 查看日志

```bash
docker compose -f /opt/flask-user/docker/docker-compose.yml logs -f app
docker compose -f /opt/flask-user/docker/docker-compose.yml logs -f nginx
```

### 重启服务

```bash
docker compose -f /opt/flask-user/docker/docker-compose.yml restart
```

### 更新部署（手动）

```bash
cd /opt/flask-user
docker compose -f docker/docker-compose.yml pull app
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml exec app flask db upgrade
```

---

## 架构总览

```
用户 ──HTTPS──► Nginx (:443) ──► Flask App (:8000) ──► PostgreSQL (:5432)
                   │
              acme.json (Let's Encrypt)
```

```
VPS 文件结构:
/opt/flask-user/
├── .env                    # 环境变量
├── docker/
│   └── docker-compose.yml  # 服务编排
├── nginx/
│   ├── app.conf            # Nginx 配置
│   └── ssl/
│       ├── fullchain.pem   # SSL 证书
│       └── privkey.pem     # SSL 私钥
└── data/                   # 数据库持久化卷
```
