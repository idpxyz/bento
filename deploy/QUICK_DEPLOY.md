# 快速部署指南

## 在 Ubuntu 服务器上快速部署

### 1. 前置要求

```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker compose version

# 确保已安装 Git
git --version
```

### 2. 上传项目（推荐使用 Git）

```bash
# 在服务器上
cd ~
git clone <your-repo-url> bento
cd bento
```

**或者使用 scp 上传**（如果项目不在 Git 中）：

```bash
# 在本地执行
rsync -avz --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
           ./ user@server:~/bento/
```

### 3. 一键部署

```bash
# 给脚本执行权限
chmod +x scripts/deploy.sh

# 运行部署脚本
./scripts/deploy.sh
```

或者手动部署：

```bash
# 进入 docker 配置目录
cd deploy/docker

# 构建并启动（生产环境）
docker compose -f compose.yml up -d --build

# 或者开发环境
docker compose -f compose.yml -f compose.dev.yaml up -d --build

# 查看日志
docker compose -f compose.yml logs -f app

# 测试
curl http://localhost:8000/health
```

### 4. 访问应用

- API: http://your-server-ip:8000
- 健康检查: http://your-server-ip:8000/health
- API 文档: http://your-server-ip:8000/docs

### 5. 常用命令

```bash
# 进入 docker 配置目录
cd deploy/docker

# 停止
docker compose -f compose.yml down

# 重启
docker compose -f compose.yml restart

# 查看状态
docker compose -f compose.yml ps

# 查看日志
docker compose -f compose.yml logs -f app
```

### 6. 更新项目

```bash
# 如果使用 Git
cd ~/bento
git pull

# 重新部署
cd deploy/docker
docker compose -f compose.yml up -d --build app
```

详细说明请查看 [DEPLOYMENT.md](./DEPLOYMENT.md)

