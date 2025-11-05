# 部署指南 - Ubuntu Docker 环境

本指南说明如何将 Bento E-commerce 项目部署到运行 Docker 的 Ubuntu 服务器上。

## 前置要求

- Ubuntu 20.04 或更高版本
- Docker Engine 20.10+ 
- Docker Compose V2 或更高版本
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间
- Git（推荐）或文件传输工具

## 1. 服务器准备

### 1.1 安装 Docker

```bash
# 更新系统
sudo apt-get update

# 安装必要的包
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 验证安装
docker --version
docker compose version
```

### 1.2 安装 Git（如果还没有）

```bash
sudo apt-get install -y git
```

### 1.3 配置 Docker（可选）

```bash
# 将当前用户添加到 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证无需 sudo 即可运行
docker ps
```

## 2. 部署应用

### 2.1 上传项目到服务器

**目标服务器**: 192.168.8.196

**推荐方式：使用 Git 克隆**

```bash
# 在服务器上创建项目目录
ssh user@192.168.8.196
mkdir -p ~/bento
cd ~/bento

# 克隆项目（推荐）
git clone <your-repo-url> .

# 或者克隆到新目录
git clone <your-repo-url> bento
cd bento
```

**备选方式：使用 rsync 上传（推荐用于手动上传）**

如果项目不在 Git 仓库中，使用 rsync（增量同步，速度快）：

```bash
# 在本地机器执行（Windows 使用 Git Bash 或 WSL）
cd /d/workspace/repo/bento  # 或你的项目路径

# 上传整个项目（排除不需要的文件）
rsync -avz --progress \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.vscode' \
    --exclude '*.db' \
    --exclude '*.sqlite' \
    --exclude '.pytest_cache' \
    --exclude 'htmlcov' \
    --exclude 'dist' \
    --exclude 'build' \
    --exclude '*.egg-info' \
    ./ user@192.168.8.196:~/bento/
```

**或者使用 scp（简单但较慢）**

```bash
# 在本地机器执行
scp -r /path/to/bento/* user@192.168.8.196:~/bento/
```

**详细的手动上传指南**: 查看 [MANUAL_UPLOAD.md](./MANUAL_UPLOAD.md)

### 2.2 项目文件说明

**必需的文件和目录：**
- `pyproject.toml` - 项目依赖配置
- `src/` - 框架源代码
- `applications/` - 应用代码
- `deploy/docker/` - Docker 配置文件
- `README.md` - 项目说明（可选）

**不需要的文件（会被 Docker 忽略）：**
- `.venv/` - 虚拟环境（Docker 会创建新的）
- `.vscode/` - IDE 配置
- `__pycache__/` - Python 缓存
- `*.db` - 本地数据库文件
- `*.md` - 文档文件（除了 README.md）
- `.git/` - Git 仓库（构建时不需要）

**注意**：`.dockerignore` 文件已经配置好，Docker 构建时会自动排除不需要的文件。

### 2.3 配置环境变量

```bash
# 进入 docker 配置目录
cd deploy/docker

# 创建环境变量文件（可选，或使用 compose.yml 中的环境变量）
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/ecommerce
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF
```

### 2.4 构建和启动服务

```bash
# 进入 docker 配置目录
cd deploy/docker

# 构建镜像并启动所有服务（生产环境）
docker compose -f compose.yml up -d --build

# 或者使用开发环境配置
docker compose -f compose.yml -f compose.dev.yaml up -d --build

# 查看日志
docker compose -f compose.yml logs -f app

# 查看所有服务状态
docker compose -f compose.yml ps
```

## 3. 验证部署

### 3.1 检查服务状态

```bash
# 进入 docker 配置目录
cd deploy/docker

# 检查所有容器是否运行
docker compose -f compose.yml ps

# 应该看到：
# - bento-ecommerce (app)
# - bento-postgres (postgres)
# - bento-redis (redis)
```

### 3.2 测试 API

```bash
# 在服务器上本地测试
curl http://localhost:8000/health

# 应该返回: {"status":"healthy"}

# 从本地机器测试（如果防火墙允许）
curl http://192.168.8.196:8000/health

# 测试 API 端点
curl http://192.168.8.196:8000/api/orders
```

## 4. 生产环境配置

### 4.1 更新数据库配置

应用已配置为从环境变量读取数据库 URL（`applications/ecommerce/runtime/composition.py`）。

### 4.2 使用环境变量文件

创建 `.env.production`:

```bash
cd deploy/docker
cat > .env.production << EOF
DATABASE_URL=postgresql+asyncpg://app:strong_password@postgres:5432/ecommerce
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-here
EOF
```

更新 `compose.yml`:

```yaml
services:
  app:
    env_file:
      - .env.production
```

### 4.3 配置反向代理（Nginx）

```bash
# 安装 Nginx
sudo apt-get install -y nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/bento
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name 192.168.8.196;  # 或使用域名

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/bento /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4.4 配置 SSL（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书（如果有域名）
# sudo certbot --nginx -d your-domain.com
# 
# 注意：如果没有域名，只能使用 HTTP，不能使用 Let's Encrypt

# 自动续期（已自动配置）
```

## 5. 数据库迁移

```bash
# 进入应用容器
docker compose -f compose.yml exec app bash

# 运行数据库迁移（如果使用 Alembic）
# alembic upgrade head

# 或者手动初始化数据库
# python -c "from applications.ecommerce.runtime.composition import init_db; import asyncio; asyncio.run(init_db())"
```

## 6. 常用命令

```bash
# 进入 docker 配置目录
cd deploy/docker

# 启动服务（生产环境）
docker compose -f compose.yml up -d

# 启动服务（开发环境）
docker compose -f compose.yml -f compose.dev.yaml up -d

# 停止服务
docker compose -f compose.yml down

# 查看日志
docker compose -f compose.yml logs -f app

# 重启服务
docker compose -f compose.yml restart app

# 更新应用（重新构建）
docker compose -f compose.yml up -d --build app

# 进入容器
docker compose -f compose.yml exec app bash

# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

## 7. 备份和恢复

### 7.1 备份数据库

```bash
# 备份 PostgreSQL
docker compose -f compose.yml exec postgres pg_dump -U app ecommerce > backup_$(date +%Y%m%d).sql

# 备份 Redis（可选）
docker compose -f compose.yml exec redis redis-cli SAVE
docker compose -f compose.yml cp redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### 7.2 恢复数据库

```bash
# 恢复 PostgreSQL
docker compose -f compose.yml exec -T postgres psql -U app ecommerce < backup_20240101.sql
```

## 8. 监控和维护

### 8.1 查看容器日志

```bash
# 实时查看应用日志
docker compose -f compose.yml logs -f app

# 查看最近 100 行日志
docker compose -f compose.yml logs --tail=100 app
```

### 8.2 健康检查

```bash
# 在服务器上检查应用健康状态
curl http://localhost:8000/health

# 从本地机器检查（如果防火墙允许）
curl http://192.168.8.196:8000/health

# 检查容器健康状态
docker compose -f compose.yml ps
```

## 9. 故障排查

### 9.1 容器无法启动

```bash
# 查看详细日志
docker compose -f compose.yml logs app

# 检查容器状态
docker compose -f compose.yml ps -a

# 进入容器调试
docker compose -f compose.yml run --rm app bash
```

### 9.2 数据库连接问题

```bash
# 测试数据库连接
docker compose -f compose.yml exec app python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def test():
    engine = create_async_engine('postgresql+asyncpg://app:app@postgres:5432/ecommerce')
    async with engine.connect() as conn:
        print('Database connected!')
asyncio.run(test())
"
```

### 9.3 端口冲突

```bash
# 检查端口占用
sudo netstat -tulpn | grep :8000

# 修改 compose.yml 中的端口映射
# ports:
#   - "8001:8000"  # 使用 8001 而不是 8000
```

## 10. 安全建议

1. **更改默认密码**: 修改 `compose.yml` 中的数据库密码
2. **使用 secrets**: 在生产环境中使用 Docker secrets 管理敏感信息
3. **限制网络访问**: 使用防火墙限制数据库和 Redis 的外部访问
4. **定期更新**: 定期更新 Docker 镜像和系统
5. **日志管理**: 配置日志轮转，避免磁盘空间耗尽

## 11. 性能优化

### 11.1 资源限制

在 `compose.yml` 中添加资源限制：

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 11.2 使用生产级 WSGI 服务器

考虑使用 Gunicorn + Uvicorn workers：

```dockerfile
CMD ["gunicorn", "applications.ecommerce.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

## 12. 项目更新流程

### 12.1 使用 Git 更新

```bash
# 在服务器上
cd ~/bento

# 拉取最新代码
git pull

# 重新构建并重启
cd deploy/docker
docker compose -f compose.yml up -d --build app
```

### 12.2 检查更新

```bash
# 查看容器日志确认更新成功
docker compose -f compose.yml logs -f app
```

## 13. 下一步

- 配置 CI/CD 流水线
- 设置监控和告警（如 Prometheus + Grafana）
- 配置日志聚合（如 ELK Stack）
- 设置自动备份
- 配置负载均衡（如果有多台服务器）
