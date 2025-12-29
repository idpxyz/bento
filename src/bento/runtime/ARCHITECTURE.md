# Bento Runtime 架构文档

## 架构概览

Bento Runtime 采用**分层、模块化**的架构设计，遵循 SOLID 原则和 DDD 最佳实践。

```
┌─────────────────────────────────────────────────────────┐
│                   BentoRuntime (核心)                    │
│                    (393 行代码)                          │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ RuntimeBuilder│   │ModuleRegistry│   │BentoContainer│
│  (配置构建)   │   │  (模块管理)  │   │   (DI容器)   │
│   177 行     │   │   146 行     │   │   113 行     │
└──────────────┘   └──────────────┘   └──────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                     集成管理层                           │
├─────────────────┬─────────────────┬─────────────────────┤
│LifecycleManager │FastAPIIntegration│PerformanceMonitor │
│    75 行        │     142 行       │      68 行          │
├─────────────────┼─────────────────┼─────────────────────┤
│ ModuleManager   │  DIIntegration  │ DatabaseManager     │
│    143 行       │     93 行        │      91 行          │
└─────────────────┴─────────────────┴─────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    功能模块层                            │
├──────────────┬──────────────┬──────────────┬───────────┤
│  lifecycle/  │ observability/│  database/   │  testing/ │
│  (生命周期)  │  (可观测性)   │  (数据库)    │  (测试)   │
└──────────────┴──────────────┴──────────────┴───────────┘
```

---

## 核心组件

### 1. BentoRuntime (核心协调器)

**职责**: 运行时核心协调器，统一所有功能的入口。

**位置**: `bootstrap.py` (393 行)

**核心方法**:
- `build_async()` - 异步构建运行时
- `create_fastapi_app()` - 创建 FastAPI 应用
- `get_startup_metrics()` - 获取启动指标

**设计模式**: Facade 模式

---

### 2. RuntimeBuilder (配置构建器)

**职责**: 通过 Builder 模式构建和配置运行时。

**位置**: `builder/runtime_builder.py` (177 行)

**核心方法**:
- `with_config()` - 配置运行时参数
- `with_modules()` - 注册模块
- `with_database()` - 配置数据库
- `build_runtime()` - 构建运行时实例

**设计模式**: Builder 模式

**示例**:
```python
runtime = (
    RuntimeBuilder()
    .with_config(service_name="my-shop", environment="prod")
    .with_database(url="postgresql://...")
    .with_modules(InfraModule(), CatalogModule())
    .build_runtime()
)
```

---

### 3. ModuleRegistry (模块注册表)

**职责**: 管理模块注册、依赖解析和拓扑排序。

**位置**: `registry.py` (146 行)

**核心方法**:
- `register()` - 注册模块
- `resolve_order()` - 拓扑排序
- `has()` - 检查模块是否存在

**设计模式**: Registry 模式

**依赖解析**:
```python
# 模块声明依赖
class CatalogModule(BentoModule):
    dependencies = ["infra"]  # 依赖 InfraModule

# Registry 自动进行拓扑排序
modules = registry.resolve_order()
# 结果: [InfraModule, CatalogModule]
```

---

### 4. BentoContainer (DI 容器)

**职责**: 依赖注入容器，管理服务的注册和获取。

**位置**: `container/base.py` (113 行)

**核心方法**:
- `set()` - 注册服务
- `get()` - 获取服务
- `register_factory()` - 注册工厂
- `create_scope()` - 创建作用域

**设计模式**: Dependency Injection

**服务生命周期**:
- **Singleton**: 全局单例
- **Transient**: 每次创建新实例
- **Scoped**: 作用域内单例

**示例**:
```python
# 注册服务
container.set("config", config)
container.set("db.engine", engine)

# 获取服务
config = container.get("config")

# 注册工厂
container.register_factory("service", lambda: MyService())
```

---

## 集成管理层

### 5. LifecycleManager (生命周期管理器)

**职责**: 协调应用的启动和关闭生命周期。

**位置**: `lifecycle/manager.py` (75 行)

**核心方法**:
- `startup()` - 运行所有启动阶段
- `shutdown()` - 运行所有关闭阶段

**生命周期阶段**:
```
启动阶段:
1. run_gates() - 合约验证
2. register_modules() - 注册模块
3. _startup_modules() - 启动模块钩子

关闭阶段:
1. _shutdown_modules() - 关闭模块钩子
2. _cleanup_database() - 清理数据库连接
```

---

### 6. FastAPIIntegration (FastAPI 集成)

**职责**: 处理 FastAPI 应用的创建和配置。

**位置**: `fastapi_integration.py` (142 行)

**核心方法**:
- `create_app()` - 创建 FastAPI 应用
- `_register_middleware()` - 注册中间件
- `_register_routers()` - 注册路由
- `_setup_health_endpoint()` - 设置健康检查

**lifespan 管理**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    await runtime.build_async()
    await lifecycle_manager._startup_modules()

    yield

    # 关闭
    await lifecycle_manager._shutdown_modules()
    await lifecycle_manager._cleanup_database()
```

---

### 7. PerformanceMonitor (性能监控)

**职责**: 监控和报告运行时性能指标。

**位置**: `performance_monitor.py` (68 行)

**核心方法**:
- `get_metrics()` - 获取启动指标
- `log_metrics()` - 记录指标日志

**监控指标**:
- `total_time` - 总启动时间
- `gates_time` - 合约验证时间
- `register_time` - 模块注册时间
- `database_time` - 数据库设置时间

---

### 8. ModuleManager (模块管理器)

**职责**: 管理模块的动态加载、卸载和重载。

**位置**: `module_manager.py` (143 行)

**核心方法**:
- `reload()` - 热重载模块
- `unload()` - 卸载模块
- `load()` - 加载模块

**使用场景**: 开发环境的热重载、动态插件系统。

---

### 9. DIIntegration (依赖注入集成)

**职责**: 为 FastAPI 提供依赖注入支持。

**位置**: `di_integration.py` (93 行)

**核心方法**:
- `get_uow()` - 获取 UnitOfWork 依赖
- `get_handler_dependency()` - 获取 Handler 依赖

**FastAPI 集成**:
```python
@router.post("/products")
async def create_product(
    uow: UnitOfWork = Depends(runtime.get_uow),
    handler: CreateProductHandler = Depends(runtime.handler_dependency),
):
    result = await handler.handle(command)
    return result
```

---

### 10. DatabaseManager (数据库管理器)

**职责**: 管理数据库连接和会话工厂。

**位置**: `database/manager.py` (91 行)

**核心方法**:
- `setup()` - 设置数据库
- `_validate_modules_requirements()` - 验证模块需求

**自动检测**:
- 检查 `DATABASE_URL` 环境变量
- 验证模块的 `requires_database` 属性
- 自动创建会话工厂

---

## 功能模块层

### 11. lifecycle/ (生命周期模块)

**组件**:
- `startup.py` (139 行) - 启动逻辑
- `shutdown.py` (50 行) - 关闭逻辑
- `manager.py` (75 行) - 生命周期协调

**核心函数**:
- `run_gates()` - 运行合约验证
- `register_modules()` - 注册模块
- `shutdown_modules()` - 关闭模块

---

### 12. observability/ (可观测性模块)

**组件**:
- `otel.py` (122 行) - OpenTelemetry 集成
- `metrics.py` (42 行) - 指标收集
- `tracing.py` (84 行) - 分布式追踪

**核心函数**:
- `setup_tracing()` - 设置追踪
- `setup_metrics()` - 设置指标

**支持的导出器**:
- Console (控制台)
- Jaeger (分布式追踪)
- Prometheus (指标)
- OTLP (通用协议)

---

### 13. database/ (数据库模块)

**组件**:
- `manager.py` (91 行) - 数据库管理器

**核心功能**:
- 自动检测数据库配置
- 创建异步会话工厂
- 验证模块数据库需求

---

### 14. testing/ (测试模块)

**组件**:
- `mocks.py` (253 行) - Mock 工具

**核心类**:
- `MockRepository` - 模拟仓储
- `MockHandler` - 模拟处理器
- `MockService` - 模拟服务

---

## 数据流

### 启动流程

```
1. RuntimeBuilder.build_runtime()
   ↓
2. BentoRuntime.__post_init__()
   ├─ 初始化 LifecycleManager
   ├─ 初始化 FastAPIIntegration
   ├─ 初始化 PerformanceMonitor
   ├─ 初始化 ModuleManager
   └─ 初始化 DIIntegration
   ↓
3. runtime.build_async()
   ├─ lifecycle_startup.run_gates()         # 合约验证
   ├─ lifecycle_startup.register_modules()  # 模块注册
   └─ DatabaseManager.setup()               # 数据库设置
   ↓
4. runtime.create_fastapi_app()
   ├─ FastAPIIntegration.create_app()
   ├─ _register_middleware()
   ├─ _register_routers()
   └─ _setup_health_endpoint()
   ↓
5. FastAPI lifespan
   ├─ _lifecycle_manager._startup_modules()  # 模块启动钩子
   └─ (yield)
   ↓
6. 应用运行
   ↓
7. FastAPI shutdown
   ├─ _lifecycle_manager._shutdown_modules() # 模块关闭钩子
   └─ _lifecycle_manager._cleanup_database() # 数据库清理
```

---

## 依赖关系图

```
BentoRuntime (核心)
├── RuntimeBuilder (构建)
│   └── RuntimeConfig (配置)
├── ModuleRegistry (注册)
│   └── BentoModule (模块)
├── BentoContainer (DI)
│   ├── ServiceLifetime (生命周期)
│   └── ContainerScope (作用域)
├── LifecycleManager (生命周期)
│   ├── lifecycle/startup
│   └── lifecycle/shutdown
├── FastAPIIntegration (FastAPI)
├── PerformanceMonitor (性能)
├── ModuleManager (模块管理)
├── DIIntegration (DI 集成)
└── DatabaseManager (数据库)
    └── DatabaseConfig (配置)
```

**依赖原则**:
- ✅ 单向依赖
- ✅ 无循环依赖
- ✅ 依赖倒置 (依赖抽象)

---

## 设计模式

| 模式 | 应用位置 | 说明 |
|------|---------|------|
| **Builder** | RuntimeBuilder | 配置与执行分离 |
| **Facade** | BentoRuntime | 统一接口 |
| **Registry** | ModuleRegistry | 模块注册和依赖解析 |
| **Dependency Injection** | BentoContainer | 松耦合 |
| **Strategy** | LifecycleManager | 可替换的生命周期策略 |
| **Observer** | 事件总线 | 解耦模块间通信 |
| **Factory** | DatabaseManager | 对象创建封装 |
| **Adapter** | FastAPIIntegration | 适配不同框架 |

---

## 扩展点

### 1. 自定义模块

```python
class MyModule(BentoModule):
    name = "my_module"
    dependencies = ["infra"]

    async def on_register(self, container):
        # 注册服务
        container.set("my_service", MyService())

    async def on_startup(self, container):
        # 启动逻辑
        pass

    async def on_shutdown(self, container):
        # 关闭逻辑
        pass
```

### 2. 自定义中间件

```python
class MyModule(BentoModule):
    def get_middleware(self):
        return [
            Middleware(MyMiddleware, config=self.config)
        ]
```

### 3. 自定义路由

```python
class MyModule(BentoModule):
    def get_routers(self):
        return [
            (my_router, "/api/v1")
        ]
```

---

## 性能特性

### 1. 异步设计

- 所有核心方法都是异步的
- 支持高并发
- 非阻塞 I/O

### 2. 延迟初始化

- DI 容器支持延迟初始化
- 按需创建服务实例
- 减少内存占用

### 3. 作用域管理

- 支持请求作用域
- 自动清理资源
- 防止内存泄漏

### 4. 拓扑排序

- O(V+E) 复杂度
- 高效的依赖解析
- 缓存排序结果

---

## 安全特性

### 1. 环境感知错误处理

- 本地环境：警告继续
- 生产环境：严格失败

### 2. 配置验证

- 启动时验证配置
- 提前发现错误
- 详细的错误消息

### 3. 资源清理

- 自动清理数据库连接
- 自动关闭模块
- 防止资源泄漏

---

## 测试策略

### 1. 单元测试

- 26 个单元测试
- 覆盖核心功能
- Mock 工具完善

### 2. 集成测试

- FastAPI 集成测试
- 数据库集成测试
- 模块集成测试

### 3. 测试模式

```python
runtime = (
    RuntimeBuilder()
    .with_test_mode(True)
    .with_mock_module("test", services={"db": mock_db})
    .build_runtime()
)
```

---

## 最佳实践

### 1. 模块设计

- ✅ 单一职责
- ✅ 明确依赖
- ✅ 生命周期钩子

### 2. 配置管理

- ✅ 使用 RuntimeBuilder
- ✅ 环境变量优先
- ✅ 配置验证

### 3. 错误处理

- ✅ 详细错误消息
- ✅ 异常链保留
- ✅ 日志记录

### 4. 性能监控

- ✅ 启动指标收集
- ✅ OpenTelemetry 集成
- ✅ 健康检查

---

## 更多信息

- [依赖说明](./DEPENDENCIES.md)
- [迁移指南](./MIGRATION.md)
- [README](./README.md)
