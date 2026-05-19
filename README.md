# Flask 用户系统

基于 Flask 的 RESTful API 用户管理系统，支持注册、登录、JWT 鉴权、管理员 CRUD 操作，**测试覆盖率 100%**，开箱即用的 Docker 部署。

## 快速开始

```bash
# 1. 安装依赖
make install

# 2. 初始化数据库
flask db upgrade

# 3. 启动开发服务器
make run
```

## API 概览

| 方法 | 端点 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 | - |
| POST | `/api/v1/auth/login` | 用户登录 | - |
| POST | `/api/v1/auth/refresh` | 刷新 Token | Bearer |
| POST | `/api/v1/auth/logout` | 登出 | Bearer |
| GET | `/api/v1/users/me` | 个人信息 | Bearer |
| PUT | `/api/v1/users/me` | 更新信息 | Bearer |
| PUT | `/api/v1/users/me/password` | 修改密码 | Bearer |
| DELETE | `/api/v1/users/me` | 注销账户 | Bearer |
| GET | `/api/v1/users` | 用户列表（管理员） | Admin |
| GET | `/api/v1/users/{id}` | 查看用户（管理员） | Admin |
| PUT | `/api/v1/users/{id}` | 更新用户（管理员） | Admin |
| DELETE | `/api/v1/users/{id}` | 删除用户（管理员） | Admin |

## 测试

```bash
make test        # 运行测试（覆盖率 100%）
make lint        # 代码检查
```

## Docker 部署

```bash
make docker-build   # 构建镜像
make docker-up      # 启动服务（需 docker compose）
```

## 生产部署（VPS）

完整的 VPS 部署指南见 [DEPLOY.md](./DEPLOY.md)，包含：

- GitHub Secrets 配置
- SSL 证书（Let's Encrypt / 自签名）
- 数据库迁移
- 日常运维命令

**仓库**: [github.com/WUIR/flask-user](https://github.com/WUIR/flask-user)

```bash
# 一键部署（需在 VPS 上执行）
bash <(curl -sL https://raw.githubusercontent.com/WUIR/flask-user/main/scripts/deploy.sh)
```

## 项目结构

```
Flask-user/
├── app/                   # 应用核心
│   ├── api/               # API 端点
│   ├── models/            # 数据模型
│   ├── schemas/           # 请求校验
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── docker/                # Docker 配置
├── nginx/                 # Nginx 反向代理
├── scripts/               # 部署脚本
├── tests/                 # 测试（100% 覆盖）
└── .github/workflows/     # CI/CD 流水线
```

## 技术栈

- **框架**: Flask 3.x
- **ORM**: SQLAlchemy + Alembic
- **认证**: JWT (access + refresh token)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **测试**: pytest + pytest-cov
- **部署**: Docker + Nginx + GitHub Actions
