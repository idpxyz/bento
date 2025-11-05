# Windows 到 Ubuntu 迁移配置调整指南

## 项目信息
- **项目**: Bento Framework (Python 项目)
- **原环境**: Windows
- **目标环境**: Ubuntu (Linux)
- **Python 版本**: 3.12

## 主要发现

### ✅ 已经兼容的部分

1. **路径处理**: 代码中已经包含了跨平台路径处理
   - `legend/infrastructure/object_storage/local.py` 文件中使用了 `replace('\\', '/')` 来规范化路径
   - 使用了 `pathlib.Path` 模块，这是跨平台的

2. **配置文件**: 配置文件格式正确
   - `pyproject.toml` - UTF-8 编码，无 Windows 特定配置
   - `Makefile` - ASCII 文本格式
   - YAML/JSON 配置文件 - 无 Windows 路径硬编码

3. **没有 Windows 特定脚本**: 未发现 `.bat`, `.cmd`, `.ps1` 文件

## 需要调整的配置

### 1. 安装依赖工具

#### 安装 uv (Python 包管理器)
```bash
# Ubuntu/Debian 方式
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 snap
snap install astral-uv

# 添加到 PATH (如果需要)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 安装其他开发工具 (可选)
```bash
# 安装 dos2unix (转换行尾符)
sudo apt update
sudo apt install dos2unix

# 安装 PostgreSQL 客户端 (如果需要本地测试)
sudo apt install postgresql-client

# 安装 Redis (如果需要本地测试)
sudo apt install redis-server

# 启动 Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 2. 数据库配置调整

#### 文件: `legend/config/database.yml`

**需要修改的配置项：**

- **默认环境 (default)**:
  ```yaml
  connection:
    host: "localhost"  # 如果 PostgreSQL 在本地，保持不变
    port: 5432
    database: "idp_dev"
    ssl_mode: "disable"  # Ubuntu 上可能需要启用 SSL
  ```

- **开发环境 (dev)**:
  ```yaml
  connection:
    host: "192.168.8.137"  # 确认此 IP 在 Ubuntu 上可访问
    port: 5438
  ```

**建议:**
- 检查网络连接配置（防火墙、网络接口）
- 如果使用 Docker，确保端口映射正确
- 在 Ubuntu 上，PostgreSQL 默认只监听 localhost，需要修改 `postgresql.conf` 和 `pg_hba.conf` 以允许远程连接

### 3. Redis 配置调整

#### 文件: `legend/config/cache.yml`

```yaml
redis:
  url: "redis://localhost:6379/0"  # 确认 Redis 服务正在运行
  pool_size: 10
  pool_timeout: 30
```

**检查 Redis 服务:**
```bash
# 检查 Redis 是否运行
systemctl status redis-server

# 测试连接
redis-cli ping
# 应该返回 PONG
```

### 4. 服务器配置

#### 文件: `legend/config/app.yml`

```yaml
server:
  host: "0.0.0.0"  # 正确，监听所有接口
  port: 8000
  workers: 4
```

**注意事项:**
- Ubuntu 上端口 < 1024 需要 root 权限
- 如果使用端口 80/443，需要使用 `sudo` 或配置 capability：
  ```bash
  sudo setcap 'cap_net_bind_service=+ep' /path/to/python
  ```

### 5. 文件权限

**在 Ubuntu 上设置执行权限:**
```bash
# 如果有 shell 脚本，设置执行权限
find . -name "*.sh" -exec chmod +x {} \;

# Makefile 通常不需要执行权限
# Python 文件也不需要执行权限（除非作为脚本直接运行）
```

### 6. Pulsar 客户端 (重要！)

#### 文件: `pyproject.toml` (第 24 行)

```toml
# Phase 5: Messaging dependencies
# "pulsar-client>=3.4",  # Apache Pulsar client (Windows not supported)
```

**好消息！** Pulsar 客户端在 Ubuntu 上是支持的。

**建议操作:**
如果项目需要使用 Pulsar，可以取消注释：

```toml
dependencies = [
  # ... 其他依赖 ...
  "pulsar-client>=3.4",  # Apache Pulsar client (Linux supported!)
]
```

**安装 Pulsar 依赖:**
```bash
# 可能需要先安装系统依赖
sudo apt install -y build-essential libssl-dev libboost-all-dev
```

### 7. 环境变量配置

创建本地环境变量文件（如果不存在）:

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=idp_dev
DB_USER=postgres
DB_PASSWORD=thends

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# Pulsar 配置 (如果启用)
PULSAR_URL=pulsar://localhost:6650

# 应用配置
ENV=dev
DEBUG=true
EOF

# 添加到 .gitignore
echo ".env" >> .gitignore
```

### 8. 项目初始化

```bash
# 1. 安装依赖
uv sync

# 或使用 pip
pip install -e ".[dev]"

# 2. 运行代码格式化
make fmt

# 3. 运行 linting
make lint

# 4. 运行测试
make test

# 5. 运行开发服务器
make dev
```

## 潜在问题和解决方案

### 问题 1: 路径分隔符
**现象**: 硬编码的 Windows 路径分隔符 `\`  
**解决**: 使用 `pathlib.Path` 或 `os.path.join()`

```python
# ❌ 不好的做法
path = "C:\\Users\\data\\file.txt"

# ✅ 好的做法
from pathlib import Path
path = Path.home() / "data" / "file.txt"
```

### 问题 2: 行尾符差异
**现象**: CRLF (Windows) vs LF (Linux)  
**解决**: 
```bash
# 转换所有 Python 文件
find . -name "*.py" -exec dos2unix {} \;

# 或配置 Git
git config core.autocrlf input
```

### 问题 3: 大小写敏感
**现象**: Windows 文件系统不区分大小写，Linux 区分  
**解决**: 确保导入语句和文件名大小写完全匹配

### 问题 4: 进程和信号
**现象**: Windows 不完全支持 POSIX 信号  
**解决**: 
```python
# 在 Linux 上可以使用
import signal
signal.signal(signal.SIGTERM, handler)
```

### 问题 5: 权限问题
**现象**: Windows 没有严格的文件权限模型  
**解决**: 
```bash
# 设置适当的权限
chmod 600 .env  # 敏感配置文件
chmod 755 scripts/  # 可执行脚本目录
```

## 性能优化建议

### 1. 使用系统服务

```bash
# 创建 systemd 服务 (可选)
sudo nano /etc/systemd/system/bento.service
```

```ini
[Unit]
Description=Bento Framework Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/workspace/bento
Environment="PATH=/home/your-username/.local/bin:/usr/bin"
ExecStart=/usr/bin/python3 -m uvicorn examples.minimal_app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. 使用 Docker (推荐)

项目中已有 `deploy/docker/` 目录，建议使用 Docker 部署：

```bash
# 检查 Docker 配置
ls -la deploy/docker/

# 使用 Docker Compose
docker-compose -f deploy/docker/docker-compose.yml up -d
```

## 验证清单

完成迁移后，请验证以下项目：

- [ ] Python 环境正确 (3.12.x)
- [ ] 所有依赖已安装 (`uv sync` 或 `pip install -e ".[dev]"`)
- [ ] PostgreSQL 连接正常
- [ ] Redis 连接正常
- [ ] 单元测试通过 (`make test`)
- [ ] 开发服务器可以启动 (`make dev`)
- [ ] API 端点可访问 (http://localhost:8000/docs)
- [ ] 日志文件可正常写入
- [ ] 文件上传/下载功能正常

## 配置优先级

建议按以下顺序调整配置：

1. ✅ **高优先级** (必须)
   - 安装 Python 3.12 和 uv
   - 配置数据库连接
   - 配置 Redis 连接
   - 设置环境变量

2. 🟨 **中优先级** (重要)
   - 启用 Pulsar 客户端 (如果需要消息队列)
   - 配置日志路径
   - 设置文件权限

3. 🟦 **低优先级** (优化)
   - 配置 systemd 服务
   - 设置 Docker 部署
   - 性能调优

## 联系和支持

如果遇到问题，可以：
1. 查看项目日志
2. 检查系统日志: `journalctl -xe`
3. 查看数据库日志: `/var/log/postgresql/`
4. 查看 Redis 日志: `/var/log/redis/`

---

**最后更新**: 2025-11-05  
**适用版本**: Bento Framework v0.1.0a2

