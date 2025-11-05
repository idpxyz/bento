# Schema注册监控系统

Schema注册监控系统是一个用于监控和管理Pulsar Schema注册状态的Web界面和API工具。它提供实时健康检查、历史记录查询、Schema验证和兼容性测试等功能。

## 主要功能

- **实时监控**: 监控所有Schema的注册状态和健康情况
- **可视化界面**: 提供直观的图表和表格展示Schema信息
- **详细信息查看**: 查看每个Schema的详细定义、历史版本和状态
- **验证测试**: 验证数据是否符合Schema定义
- **兼容性检查**: 检查新Schema是否与现有Schema兼容
- **指标统计**: 展示Schema注册成功率和常见错误

## 安装和运行

### 前提条件

- Python 3.8+
- FastAPI
- 访问权限到Pulsar Admin API

### 安装

项目已经集成到IDP框架中，无需单独安装。

### 运行API服务

使用以下命令启动API服务：

```bash
# 开发模式（自动重载和调试信息）
make -C src/idp/framework/infrastructure/schema api-dev

# 生产模式
make -C src/idp/framework/infrastructure/schema api-prod

# 默认为开发模式
make -C src/idp/framework/infrastructure/schema api
```

或者直接使用Python命令：

```bash
python -m idp.framework.api.schema.cli --host 0.0.0.0 --port 8000
```

服务启动后，访问 http://localhost:8000 查看Web界面。

## API接口

系统提供以下API接口：

### 健康检查

```
GET /schema-monitor/health?pulsar_admin_url={url}
```

执行Schema健康检查，返回所有Schema的状态。

### 注册表信息

```
GET /schema-monitor/registry
```

返回Schema注册表的概览信息，包括总数、类型分布等。

### Schema详情

```
GET /schema-monitor/schema/{schema_name}
```

获取指定Schema的详细信息。

### Schema历史

```
GET /schema-monitor/schema/{schema_name}/history
```

获取指定Schema的历史版本记录。

### 验证数据

```
POST /schema-monitor/schema/{schema_name}/validate
Content-Type: application/json

{
  "data": {
    "field1": "value1",
    ...
  }
}
```

验证数据是否符合Schema定义。

### 兼容性检查

```
POST /schema-monitor/schema/{schema_name}/compatibility
Content-Type: application/json

{
  "schema": {
    // 新Schema定义
  }
}
```

检查新Schema是否与现有Schema兼容。

### 获取指标

```
GET /schema-monitor/metrics?days={days}
```

获取Schema注册指标数据。

### 获取历史记录

```
GET /schema-monitor/history?limit={limit}
```

获取健康检查的历史记录。

## 命令行工具

除了Web界面和API外，还提供命令行工具进行Schema状态检查：

```bash
# 执行Schema健康检查
make -C src/idp/framework/infrastructure/schema schema-check url=http://pulsar-admin:8080

# 启动持续监控
make -C src/idp/framework/infrastructure/schema schema-monitor url=http://pulsar-admin:8080

# 初始化监控历史记录
make -C src/idp/framework/infrastructure/schema schema-monitor-init url=http://pulsar-admin:8080
```

## 配置选项

启动API服务时可以使用以下命令行参数：

- `--host`: 绑定的主机地址，默认为 0.0.0.0
- `--port`: 监听的端口号，默认为 8000
- `--reload`: 启用自动重载（开发模式）
- `--debug`: 启用调试模式

## 问题排查

常见问题及解决方案：

1. **无法连接到Pulsar Admin API**
   - 检查Pulsar服务是否正常运行
   - 确认Pulsar Admin URL是否正确
   - 检查网络连接和防火墙设置

2. **Schema注册失败**
   - 检查Schema格式是否正确
   - 查看详细错误消息了解具体原因
   - 确认Schema类型与之前注册的类型一致

3. **Web界面无法加载**
   - 检查API服务是否正常运行
   - 清除浏览器缓存后重试
   - 检查浏览器控制台是否有错误信息

## 贡献

欢迎贡献代码、报告问题或提出改进建议。请遵循项目的代码规范和贡献指南。 