# IDP 框架配置系统

配置系统提供了一种灵活且类型安全的方式来管理应用程序的配置。它支持从多种源（如环境变量、YAML）加载配置，并使用 Pydantic 模型进行验证和类型转换。

## 设计原则

- **类型安全**：使用 Pydantic 模型进行配置验证和类型转换
- **多源加载**：支持从环境变量、YAML 等多种源加载配置
- **优先级管理**：支持配置优先级，高优先级的配置会覆盖低优先级的配置
- **关注点分离**：框架配置与应用配置分离
- **可扩展性**：应用可以注册自己的配置模型和提供器
- **环境隔离**：支持不同环境（dev、test、prod）的配置隔离

## 核心组件

### 配置管理器（ConfigManager）

`ConfigManager` 是配置系统的核心组件，负责注册、加载和管理配置。它提供了以下主要功能：

- 配置提供器注册和管理
- 配置合并和优先级处理
- 配置变更监听
- 环境特定配置管理

### 配置提供器（ConfigProvider）

配置提供器负责从特定源加载配置数据。框架提供了以下内置提供器：

- `YamlProvider`：从 YAML 文件加载配置，支持环境特定配置
- `EnvProvider`：从环境变量加载配置，支持复合词和路径转换

## 基本用法

### 1. 定义配置模型

使用 Pydantic 模型定义配置结构和验证规则：

```python
from pydantic import BaseModel, Field

class ConnectionConfig(BaseModel):
    host: str = Field(..., description="数据库主机")
    port: int = Field(5432, description="端口")
    database: str = Field(..., description="数据库名")
    db_schema: str = Field("public", description="模式")
    ssl_mode: str = Field("disable", description="SSL模式")

class DatabaseConfig(BaseModel):
    type: str = Field("postgresql", description="数据库类型")
    connection: ConnectionConfig
    credentials: CredentialsConfig
    pool: PoolConfig
```

### 2. 创建配置文件

database.yml:
```yaml
# 默认配置
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

# 测试环境配置
test:
  connection:
    database: "idp_test"
  credentials:
    username: "test_user"
    password: "test_pass"
  pool:
    max_size: 5
```

### 3. 加载配置

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

## 环境变量配置

环境变量配置遵循以下命名规则：

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
# 测试环境数据库配置
DB_TEST_TYPE=postgresql
DB_TEST_CONNECTION_PORT=5437
DB_TEST_CONNECTION_DATABASE=iot_test
DB_TEST_CREDENTIALS_USERNAME=test_user
DB_TEST_CREDENTIALS_PASSWORD=test_pass
DB_TEST_POOL_MAX_SIZE=5
```

## 配置变更监听

配置系统支持配置变更监听，可以在配置更新时执行自定义操作：

```python
def config_change_listener(config: Dict[str, Any]) -> None:
    """配置变更监听器"""
    logger.info("配置已更新:")
    for key, value in config.items():
        if isinstance(value, dict):
            logger.info(f"  {key}:")
            for k, v in value.items():
                logger.info(f"    {k}: {v}")
        else:
            logger.info(f"  {key}: {value}")

# 添加监听器
config_manager.add_change_listener("database", config_change_listener)
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

## 更多信息

- [使用指南](./USAGE.md)
- [示例代码](./demo/)
- [API参考](./API.md)