# Ubuntu 环境快速参考

> 从 Windows 迁移到 Ubuntu 的快速命令参考

## 🚀 快速开始（5 分钟）

```bash
# 1. 运行自动设置脚本
./setup_ubuntu.sh

# 2. 启动开发环境（Docker）
cd deploy/docker
./start.sh dev

# 3. 或者本地开发（不用 Docker）
make dev
```

访问: http://localhost:8000/docs

## 📋 常用命令对照表

### 项目管理

| 操作 | 命令 |
|------|------|
| 格式化代码 | `make fmt` |
| 代码检查 | `make lint` |
| 运行测试 | `make test` |
| 启动开发服务器 | `make dev` |
| 运行示例 | `make run` |

### Docker 操作

| 操作 | 命令 |
|------|------|
| 启动开发环境 | `./start.sh dev` |
| 启动生产环境 | `./start.sh prod` |
| 重新构建 | `./start.sh dev --build` |
| 停止服务 | `./start.sh --down` |
| 查看日志 | `./start.sh --logs` |
| 清理数据 | `./start.sh --clean` |

### Python 环境

| 操作 | 命令 |
|------|------|
| 创建虚拟环境 | `uv venv` |
| 激活虚拟环境 | `source .venv/bin/activate` |
| 安装依赖 | `uv sync` 或 `pip install -e ".[dev]"` |
| 查看已安装包 | `uv pip list` |
| 退出虚拟环境 | `deactivate` |

### 数据库操作

| 操作 | 命令 |
|------|------|
| 连接 PostgreSQL | `psql -h localhost -U postgres -d bento_db` |
| 查看数据库列表 | `\l` (在 psql 中) |
| 查看表列表 | `\dt` (在 psql 中) |
| 退出 psql | `\q` |
| 备份数据库 | `pg_dump -U postgres bento_db > backup.sql` |
| 恢复数据库 | `psql -U postgres bento_db < backup.sql` |

### Redis 操作

| 操作 | 命令 |
|------|------|
| 连接 Redis | `redis-cli` |
| 测试连接 | `redis-cli ping` |
| 查看所有键 | `KEYS *` (在 redis-cli 中) |
| 清空数据库 | `FLUSHDB` (在 redis-cli 中) |
| 退出 redis-cli | `exit` |

### 系统服务

| 操作 | 命令 |
|------|------|
| 启动 PostgreSQL | `sudo systemctl start postgresql` |
| 启动 Redis | `sudo systemctl start redis-server` |
| 启动 Docker | `sudo systemctl start docker` |
| 查看服务状态 | `sudo systemctl status <service>` |
| 设置开机自启 | `sudo systemctl enable <service>` |
| 重启服务 | `sudo systemctl restart <service>` |

### 文件和权限

| 操作 | 命令 |
|------|------|
| 给脚本执行权限 | `chmod +x script.sh` |
| 修改文件权限 | `chmod 644 file.txt` |
| 修改目录权限 | `chmod 755 directory/` |
| 查看文件权限 | `ls -la` |
| 更改所有者 | `chown user:group file.txt` |

### 端口和网络

| 操作 | 命令 |
|------|------|
| 查看端口占用 | `sudo netstat -tulpn \| grep :8000` |
| 查看进程占用端口 | `sudo lsof -i :8000` |
| 测试端口可访问性 | `curl http://localhost:8000` |
| 允许端口通过防火墙 | `sudo ufw allow 8000/tcp` |
| 查看防火墙状态 | `sudo ufw status` |

### Git 操作

| 操作 | 命令 |
|------|------|
| 配置行尾符 | `git config core.autocrlf input` |
| 查看状态 | `git status` |
| 暂存所有更改 | `git add .` |
| 提交 | `git commit -m "message"` |
| 查看差异 | `git diff` |

## 🔧 故障排除速查

### Python 问题

```bash
# ImportError
export PYTHONPATH="/workspace/bento:/workspace/bento/src"

# 虚拟环境问题
rm -rf .venv && uv venv && uv sync

# 权限问题
chmod -R u+w .venv/
```

### Docker 问题

```bash
# 权限被拒绝
sudo usermod -aG docker $USER
newgrp docker

# 容器无法启动
docker compose down && docker compose up -d --build

# 清理旧数据
docker system prune -a --volumes
```

### 数据库问题

```bash
# PostgreSQL 连接失败
sudo systemctl start postgresql
sudo systemctl status postgresql

# 重置 PostgreSQL 密码
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'newpassword';"

# 创建数据库
sudo -u postgres createdb bento_db
```

### Redis 问题

```bash
# Redis 无法启动
sudo systemctl start redis-server
sudo systemctl status redis-server

# Redis 连接超时
redis-cli ping

# 清空 Redis 缓存
redis-cli FLUSHALL
```

### 端口冲突

```bash
# 找出占用进程
sudo lsof -i :8000

# 杀死进程
sudo kill -9 <PID>

# 或修改配置文件中的端口
```

## 📁 重要文件路径

| 文件 | 路径 |
|------|------|
| 项目配置 | `pyproject.toml` |
| 应用配置 | `legend/config/app.yml` |
| 数据库配置 | `legend/config/database.yml` |
| 缓存配置 | `legend/config/cache.yml` |
| 环境变量 | `.env` (需自己创建) |
| Docker 配置 | `deploy/docker/` |
| 迁移指南 | `MIGRATION_UBUNTU.md` |
| 检查清单 | `UBUNTU_CHECKLIST.md` |

## 🌐 默认端口

| 服务 | 端口 | 访问地址 |
|------|------|---------|
| 应用 API | 8000 | http://localhost:8000 |
| API 文档 | 8000 | http://localhost:8000/docs |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Redpanda (Kafka) | 19092 | localhost:19092 |
| MinIO API | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 |

## 🔐 默认凭据（开发环境）

| 服务 | 用户名 | 密码 |
|------|--------|------|
| PostgreSQL | app | app |
| MinIO | minio | minio123 |
| Redis | - | (无密码) |

**⚠️ 生产环境必须修改默认密码！**

## 📊 系统资源要求

| 环境 | RAM | CPU | 磁盘 |
|------|-----|-----|------|
| 最低配置 | 2GB | 2核 | 10GB |
| 推荐配置 | 4GB+ | 4核 | 20GB+ |
| 生产环境 | 8GB+ | 4核+ | 50GB+ |

## 🔍 快速诊断命令

一键检查所有关键服务：

```bash
#!/bin/bash
echo "=== 系统信息 ==="
uname -a
echo ""

echo "=== Python 版本 ==="
python3 --version
echo ""

echo "=== Docker 状态 ==="
docker --version
docker compose version
systemctl is-active docker
echo ""

echo "=== 数据库状态 ==="
systemctl is-active postgresql
systemctl is-active redis-server
echo ""

echo "=== 端口检查 ==="
echo "8000: $(netstat -tuln | grep ':8000' || echo '可用')"
echo "5432: $(netstat -tuln | grep ':5432' || echo '可用')"
echo "6379: $(netstat -tuln | grep ':6379' || echo '可用')"
echo ""

echo "=== 磁盘空间 ==="
df -h | grep -E '^/dev/'
echo ""

echo "=== 内存使用 ==="
free -h
```

保存为 `check_system.sh`，执行 `chmod +x check_system.sh && ./check_system.sh`

## 📚 相关文档

- **完整迁移指南**: `cat MIGRATION_UBUNTU.md`
- **检查清单**: `cat UBUNTU_CHECKLIST.md`
- **Docker 文档**: `cat deploy/docker/README.md`
- **项目文档**: `cat README.md`

## 💡 小贴士

1. **使用别名简化命令**:
   ```bash
   echo "alias dc='docker compose'" >> ~/.bashrc
   echo "alias dcup='docker compose up -d'" >> ~/.bashrc
   echo "alias dcdown='docker compose down'" >> ~/.bashrc
   source ~/.bashrc
   ```

2. **监控服务**:
   ```bash
   watch -n 2 'docker ps'
   ```

3. **查看实时日志**:
   ```bash
   docker compose logs -f app
   ```

4. **快速重启应用**:
   ```bash
   docker compose restart app
   ```

5. **进入容器调试**:
   ```bash
   docker exec -it bento-app bash
   ```

---

**版本**: 1.0  
**最后更新**: 2025-11-05  
**适用环境**: Ubuntu 20.04+

