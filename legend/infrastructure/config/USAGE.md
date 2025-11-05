# IDP 配置系统使用指南

本指南将介绍如何使用 IDP 框架的配置系统。配置系统支持多源配置加载、环境特定配置、类型安全和自动验证。

## 目录

- [基本概念](#基本概念)
- [快速开始](#快速开始)
- [配置源](#配置源)
- [环境变量命名规则](#环境变量命名规则)
- [最佳实践](#最佳实践)
- [完整示例](#完整示例)

## 基本概念

IDP 配置系统的核心概念：

1. **配置段（Section）**：使用 Pydantic 模型定义的配置结构
2. **配置提供器（Provider）**：负责从特定源加载配置
3. **环境（Environment）**：如 dev、test、prod 等不同运行环境
4. **配置合并（Merge）**：按优先级合并不同源的配置

## 快速开始

### 1. 定义配置模型

```python
from pydantic import BaseModel, Field

class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    type: str = Field("postgresql", description="数据库类型")
    connection: ConnectionConfig
    credentials: CredentialsConfig
    pool: PoolConfig
    
    class Config:
        validate_assignment = True
```

### 2. 创建配置文件

database.yml:
```yaml
default:
  type: "postgresql"
  connection:
    host: "localhost"
    port: 5432
    database: "idp"
    db_schema: "public"
  credentials:
    username: "postgres"
    password: "postgres"
  pool:
    min_size: 1
    max_size: 10

test:
  connection:
    database: "idp_test"
  credentials:
    username: "test_user"
    password: "test_pass"
  pool:
    max_size: 5
```

### 3. 设置环境变量

```bash
# 测试环境数据库配置
DB_TEST_TYPE=postgresql
DB_TEST_CONNECTION_PORT=5437
DB_TEST_CONNECTION_DATABASE=iot_test
DB_TEST_CREDENTIALS_USERNAME=test_user
DB_TEST_CREDENTIALS_PASSWORD=test_pass
DB_TEST_POOL_MAX_SIZE=5
```

### 4. 加载配置

```python
from idp.framework.infrastructure.config.core.manager import ConfigManager
from idp.framework.infrastructure.config.providers.yaml import YamlProvider
from idp.framework.infrastructure.config.providers.env import EnvProvider

async def setup_database_config(env_name: str = "dev"):
    """设置数据库配置"""
    config_manager = ConfigManager()
    
    # 注册提供器并合并配置
    config = await config_manager.register_and_merge([
        YamlProvider(
            namespace="database",
            file_paths=["config/database.yml"],
            required=True,
            env_name=env_name
        ),
        EnvProvider(
            namespace="database",
            env_name=env_name,
            prefix="DB",
            config_dir="config"
        )
    ], model=DatabaseConfig)
    
    return config
```

## 配置源

### 1. YAML 配置

- 支持默认配置和环境特定配置
- 配置按环境名称分段
- 环境配置继承并覆盖默认配置

```yaml
# 默认配置
default:
  setting1: value1
  setting2: value2

# 环境特定配置
dev:
  setting1: dev_value1
test:
  setting1: test_value1
prod:
  setting1: prod_value1
```

### 2. 环境变量

- 使用前缀区分不同配置段
- 支持点分隔的配置路径
- 环境变量优先级高于 YAML 配置

## 环境变量命名规则

环境变量遵循以下命名规则：

1. **基本格式**：`{PREFIX}_{ENV}_{PATH}`
   - PREFIX：配置段前缀（如 DB、APP）
   - ENV：环境名称（如 DEV、TEST、PROD）
   - PATH：配置路径，使用下划线分隔

2. **路径转换**：
   - 环境变量：`DB_TEST_CONNECTION_HOST`
   - 配置路径：`connection.host`

3. **复合词处理**：
   - 环境变量：`DB_CONNECTION_DB_SCHEMA`
   - 配置路径：`connection.db_schema`

示例：
```bash
# 应用配置
APP_TEST_DEBUG=true
APP_TEST_SECRET_KEY=test-key

# 数据库配置
DB_TEST_CONNECTION_HOST=localhost
DB_TEST_CONNECTION_PORT=5432
DB_TEST_POOL_MAX_SIZE=5
```

## 最佳实践

1. **配置分层**
   - 使用默认配置定义基础值
   - 在环境配置中只覆盖需要改变的值
   - 使用环境变量处理敏感信息

2. **类型安全**
   - 使用 Pydantic 模型定义配置结构
   - 为所有字段添加类型注解
   - 使用 Field 定义约束和默认值

3. **配置验证**
   - 在模型中定义验证规则
   - 使用 validator 装饰器添加自定义验证
   - 处理配置加载异常

4. **敏感信息处理**
   - 不在代码或 YAML 中存储敏感信息
   - 使用环境变量传递敏感配置
   - 在日志中隐藏敏感信息

## 完整示例

### 1. 配置结构

```
myapp/
├── config/
│   ├── database.yml
│   ├── app.yml
│   └── .env
├── models/
│   └── config.py
└── main.py
```

### 2. 配置模型

```python
# models/config.py
from pydantic import BaseModel, Field

class ConnectionConfig(BaseModel):
    host: str = Field(..., description="数据库主机")
    port: int = Field(5432, description="端口")
    database: str = Field(..., description="数据库名")
    db_schema: str = Field("public", description="模式")
    ssl_mode: str = Field("disable", description="SSL模式")

class CredentialsConfig(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

class PoolConfig(BaseModel):
    min_size: int = Field(1, description="最小连接数")
    max_size: int = Field(10, description="最大连接数")
    max_queries: int = Field(50000, description="最大查询数")

class DatabaseConfig(BaseModel):
    type: str = Field("postgresql", description="数据库类型")
    connection: ConnectionConfig
    credentials: CredentialsConfig
    pool: PoolConfig
```

### 3. 配置加载

```python
# main.py
import asyncio
from pathlib import Path
from idp.framework.infrastructure.config.core.manager import ConfigManager
from idp.framework.infrastructure.config.providers.yaml import YamlProvider
from idp.framework.infrastructure.config.providers.env import EnvProvider
from models.config import DatabaseConfig

async def setup_config():
    config_dir = Path(__file__).parent / "config"
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    # 注册提供器并合并配置
    db_config = await config_manager.register_and_merge([
        YamlProvider(
            namespace="database",
            file_paths=[str(config_dir / "database.yml")],
            required=True,
            env_name="test"
        ),
        EnvProvider(
            namespace="database",
            env_name="test",
            prefix="DB",
            config_dir=str(config_dir)
        )
    ], model=DatabaseConfig)
    
    return db_config

if __name__ == "__main__":
    config = asyncio.run(setup_config())
    print(f"数据库配置已加载: {config.connection.database}")
```

### 4. 运行示例

```bash
# 设置环境变量
export DB_TEST_CONNECTION_PORT=5437
export DB_TEST_CONNECTION_DATABASE=iot_test
export DB_TEST_CREDENTIALS_USERNAME=test_user
export DB_TEST_CREDENTIALS_PASSWORD=test_pass
export DB_TEST_POOL_MAX_SIZE=5

# 运行程序
python main.py
```

## 更多信息

- [配置系统API文档](./README.md)
- [示例代码](./demo/)
- [配置模型参考](./models/)