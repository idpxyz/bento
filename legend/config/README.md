# 配置系统使用说明

IDP框架配置系统提供了灵活的配置管理功能，支持基于环境的配置加载和覆盖。

## 配置目录结构

配置系统支持以下目录结构:

```
framework/
├── config/             # 基础配置目录
│   ├── app.yml         # 应用配置
│   ├── database.yml    # 数据库配置
│   ├── logger.yml      # 日志配置
│   └── ...             # 其他基础配置
│
├── config/dev/         # 开发环境特定配置 (覆盖基础配置)
│   ├── app.yml
│   ├── database.yml
│   └── ...
│
├── config/prod/        # 生产环境特定配置
│   ├── app.yml
│   ├── database.yml
│   └── ...
│
├── .env                # 默认环境变量
├── .env.dev            # 开发环境变量
├── .env.prod           # 生产环境变量
└── ...
```

## 配置加载顺序

配置系统按照以下顺序加载配置:

1. 环境变量文件 (`.env.{env_name}`)
2. 基础配置文件 (`config/*.yml`)
3. 环境特定配置文件 (`config/{env_name}/*.yml`)

较低层级的配置会被较高层级的配置覆盖，确保环境特定的配置可以覆盖默认配置。

## 创建环境配置

要创建新的环境配置，可以使用提供的工具脚本:

```bash
python -m idp.framework.create_env_configs dev
```

或手动创建:

1. 创建环境配置目录: `mkdir -p config/dev`
2. 从基础配置复制并修改: `cp config/app.yml config/dev/app.yml`
3. 创建环境变量文件: `touch .env.dev`

## 配置访问API

在代码中访问配置:

```python
from idp.framework.infrastructure.config.manager import config

# 获取特定命名空间的配置
app_config = config.get_namespace("app")
db_config = config.get_namespace("database")

# 获取特定配置项
debug_mode = config.get("app.debug")
database_url = config.get("database.url")
```

## 配置文件格式

配置文件使用YAML格式，示例:

```yaml
# app.yml
app_name: "IDP API"
version: "1.0.0"
debug: false
cors_enabled: true
cors_origins:
  - "http://localhost:3000"
  - "https://example.com"
```

## 环境变量覆盖

可以使用环境变量覆盖配置文件中的设置。环境变量的格式为:

```
APP_DEBUG=true
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

环境变量会覆盖配置文件中的相应设置。

## 调试配置加载

可以使用测试工具验证配置加载:

```bash
python -m idp.framework.test_config_load dev
python -m idp.framework.test_config_load prod --verbose
```

## 常见问题解决

1. **配置加载失败**: 检查环境变量文件和配置目录结构是否正确
2. **配置不生效**: 确认加载顺序和优先级
3. **找不到配置文件**: 使用绝对路径或正确的相对路径

## 最佳实践

1. 在基础配置中设置默认值
2. 针对不同环境创建特定配置
3. 敏感信息使用环境变量
4. 使用类型提示和验证确保配置类型安全 