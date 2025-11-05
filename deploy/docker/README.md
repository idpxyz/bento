# Docker 部署配置

本目录包含 Docker 部署相关的配置文件。

## 文件说明

- **`Dockerfile`** - 应用镜像构建文件
- **`compose.yml`** - 生产环境 Docker Compose 配置（基础配置）
- **`compose.dev.yaml`** - 开发环境 Docker Compose 配置（覆盖文件）

## 为什么需要两个 Compose 文件？

这是 Docker Compose 的**多文件配置模式**，设计理念是：

### `compose.yml`（基础配置）
- 包含所有服务的**完整定义**
- 适用于**生产环境**
- 包含核心服务：app、postgres、redis

### `compose.dev.yaml`（覆盖配置）
- **只包含需要修改或新增的配置**
- 通过**合并**的方式覆盖基础配置
- 开发环境的特殊需求：
  - 代码热重载（代码挂载）
  - 开发模式环境变量（DEBUG、development）
  - 额外的开发工具（redpanda、minio）

### 优点
1. **避免重复** - 不需要在两个文件中重复定义相同的配置
2. **易于维护** - 基础配置变更只需改一个文件
3. **清晰分离** - 生产环境和开发环境的差异一目了然
4. **灵活组合** - 可以轻松添加更多环境（如 staging）

### 合并规则
Docker Compose 会按顺序合并文件，**后指定的文件会覆盖先指定文件中相同的键**。

例如：
- `compose.yml` 中 `app.environment.ENVIRONMENT = production`
- `compose.dev.yaml` 中 `app.environment.ENVIRONMENT = development`
- 最终结果：`ENVIRONMENT = development`（开发环境的覆盖了生产环境）

## 快速开始

我们提供了便捷的启动脚本 `start.sh`，适配 Ubuntu/Linux 环境：

### 使用启动脚本（推荐）

```bash
# 进入 Docker 目录
cd deploy/docker

# 启动开发环境（带热重载和额外服务）
./start.sh dev

# 启动生产环境
./start.sh prod

# 重新构建并启动
./start.sh dev --build

# 停止所有服务
./start.sh --down

# 查看日志
./start.sh --logs

# 查看帮助
./start.sh --help
```

### 手动启动（不使用脚本）

#### 生产环境

```bash
# 在项目根目录执行
cd deploy/docker
docker compose -f compose.yml up -d --build
```

#### 开发环境

```bash
# 在项目根目录执行
cd deploy/docker
docker compose -f compose.yml -f compose.dev.yaml up -d --build
```

## 服务说明

### 核心服务（两个环境都有）

- **app** - E-commerce 应用（FastAPI）
- **postgres** - PostgreSQL 数据库
- **redis** - Redis 缓存

### 开发环境额外服务

- **redpanda** - Kafka 兼容的消息队列（用于测试）
- **minio** - 对象存储服务（用于测试）

## 开发环境 vs 生产环境差异

| 特性 | 生产环境 | 开发环境 |
|------|---------|---------|
| 代码挂载 | ❌ | ✅ (热重载) |
| 环境变量 | `ENVIRONMENT=production` | `ENVIRONMENT=development` |
| 日志级别 | `INFO` | `DEBUG` |
| Uvicorn 参数 | 默认 | `--reload` |
| 数据库镜像 | `postgres:16-alpine` | `postgres:16` |
| Redis 镜像 | `redis:7-alpine` | `redis:7` |
| 额外服务 | 无 | redpanda, minio |
| 数据卷 | `postgres_data` | `postgres_dev_data` |

## 端口映射

- `8000` - 应用 API
- `5432` - PostgreSQL
- `6379` - Redis
- `9092` - Redpanda (仅开发环境)
- `9000` - MinIO API (仅开发环境)
- `9001` - MinIO Console (仅开发环境)

## 环境变量

主要环境变量在 `compose.yml` 中配置，开发环境在 `compose.dev.yaml` 中覆盖：

- `DATABASE_URL` - 数据库连接字符串
- `REDIS_URL` - Redis 连接字符串
- `ENVIRONMENT` - 环境类型（production/development）
- `LOG_LEVEL` - 日志级别（INFO/DEBUG）

## Ubuntu/Linux 特定注意事项

### 1. 文件权限
```bash
# 确保脚本有执行权限
chmod +x start.sh

# 如果遇到权限问题，可能需要将用户加入 docker 组
sudo usermod -aG docker $USER
# 需要重新登录才能生效
```

### 2. 防火墙配置
```bash
# 如果需要从外部访问，允许端口通过防火墙
sudo ufw allow 8000/tcp  # 应用 API
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis
```

### 3. SELinux（如果启用）
```bash
# 如果遇到卷挂载问题，可能需要调整 SELinux 上下文
chcon -Rt svirt_sandbox_file_t /workspace/bento
```

### 4. 资源限制
开发环境（特别是 Redpanda）可能需要较多资源：
- 最低要求：2GB RAM
- 推荐配置：4GB+ RAM，2+ CPU 核心

## 常见问题

### 问题 1: 端口已被占用
```bash
# 检查端口占用
sudo netstat -tulpn | grep ':8000'
# 或
sudo lsof -i :8000

# 修改 compose.yml 中的端口映射
ports:
  - "8001:8000"  # 改为其他端口
```

### 问题 2: 容器无法访问网络
```bash
# 重启 Docker 服务
sudo systemctl restart docker

# 检查 Docker 网络
docker network ls
docker network inspect bento-network
```

### 问题 3: 数据库初始化失败
```bash
# 清理并重新创建数据卷
./start.sh --clean
./start.sh dev --build
```

### 问题 4: 权限被拒绝（Permission denied）
```bash
# 检查 Docker 守护进程状态
sudo systemctl status docker

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker  # 或重新登录
```

## 性能优化

### 开发环境优化
```yaml
# 在 compose.dev.yaml 中调整资源限制
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 日志管理
```bash
# 限制日志大小，在 compose.yml 中添加
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 监控和调试

### 查看服务状态
```bash
docker compose -f compose.yml -f compose.dev.yaml ps
```

### 进入容器
```bash
# 进入应用容器
docker exec -it bento-app bash

# 进入数据库容器
docker exec -it bento-postgres psql -U app -d bento_db
```

### 查看实时日志
```bash
# 所有服务
docker compose -f compose.yml -f compose.dev.yaml logs -f

# 特定服务
docker compose -f compose.yml -f compose.dev.yaml logs -f app
```

### 资源使用情况
```bash
docker stats
```

## 备份和恢复

### 备份数据库
```bash
# 创建备份目录
mkdir -p /workspace/bento/backups

# 备份 PostgreSQL
docker exec bento-postgres pg_dump -U app bento_db > backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢复数据库
```bash
# 恢复备份
docker exec -i bento-postgres psql -U app -d bento_db < backups/backup_20251105_120000.sql
```

## 注意事项

1. **构建上下文**: Dockerfile 使用项目根目录作为构建上下文（`context: ../..`）
2. **数据持久化**: 
   - 生产环境：`postgres_data`, `redis_data`, `app_data`
   - 开发环境：`postgres_dev_data`, `minio_dev_data`（独立数据卷，互不影响）
3. **健康检查**: 所有服务都配置了健康检查，确保依赖服务就绪后再启动应用
4. **代码挂载**: 开发环境挂载整个项目目录，修改代码后自动重载（无需重建镜像）
5. **应用入口**: 当前配置使用 `examples.minimal_app.main:app` 作为入口点，如需更改请修改 Dockerfile 和 compose 文件中的启动命令

## 更多信息

- 详细部署说明请查看项目根目录的 `MIGRATION_UBUNTU.md` 文件
- 快速部署指南: `QUICK_DEPLOY.md`
- 项目主文档: `README.md`
