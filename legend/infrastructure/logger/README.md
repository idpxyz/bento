# IDP Logger Module

A high-performance, configurable, and extensible logging system built on top of `structlog` with async support.

## Features

- **Async Processing**: Non-blocking log processing with configurable queue sizes
- **Multiple Output Handlers**:
  - Console output with JSON or pretty format
  - File output with rotation support
  - Sentry integration for error tracking
  - Logstash integration for centralized logging
  - Kafka integration for log streaming
- **Type Safety**: Full type hints and Pydantic model validation
- **Configurable**: YAML-based configuration with environment variable support
- **Performance Optimized**: Async queues and batch processing
- **Extensible**: Easy to add new log handlers

## Architecture

```
logger/
├── models.py           # Configuration models
├── processors/         # Log processors
│   ├── base.py        # Base async processor
│   ├── console.py     # Console output
│   ├── file.py        # File output with rotation
│   ├── sentry.py      # Sentry integration
│   ├── logstash.py    # Logstash integration
│   └── kafka.py       # Kafka integration
└── setup.py           # Logger setup and initialization
```

## Usage

### Basic Usage

```python
from idp.framework.infrastructure.logger import logger_setup, logger_manager

# Initialize logger
await logger_setup()

# Get a logger instance
logger = logger_manager.get_logger(__name__)

# Log messages
logger.info("Hello, world!", extra_field="value")
logger.error("An error occurred", error_code=500)
```

### Configuration

Configuration is done via YAML files and environment variables:

```yaml
default:
  console:
    enabled: true
    level: INFO
    format: json
    queue_size: 1000

  file:
    enabled: true
    level: INFO
    file_path: logs/app.log
    max_size: 10485760  # 10MB
    backup_count: 5
    queue_size: 1000

  sentry:
    enabled: false
    level: ERROR
    dsn: ""
    environment: production
    queue_size: 1000
```

### Custom Processor Implementation

To create a new processor:

1. Define configuration model in `models.py`:
```python
class MyHandlerConfig(BaseHandlerConfig):
    custom_field: str = Field(...)
```

2. Implement processor in `processors/`:
```python
class MyProcessor(AsyncProcessor[MyHandlerConfig]):
    def __init__(self, config: MyHandlerConfig):
        super().__init__(config)
        
    async def setup(self) -> None:
        # Initialize resources
        pass
        
    async def process_event_async(self, logger, method_name, event_dict):
        # Process log event
        pass
```

## Handler Details

### Console Handler
- Supports JSON and pretty printing formats
- Colorized output in development mode
- Configurable log levels

### File Handler
- Automatic file rotation based on size
- Configurable backup count
- Async file I/O operations
- JSON formatted output

### Sentry Handler
- Error tracking and monitoring
- Environment-aware configuration
- Automatic context enrichment

### Logstash Handler
- HTTP transport to Logstash
- Configurable connection timeout
- Automatic reconnection

### Kafka Handler
- Batch processing support
- Configurable compression
- High-throughput event streaming

## Performance Considerations

- Each handler runs in its own async queue
- Configurable queue sizes to prevent memory issues
- Batch processing where applicable (Kafka)
- Non-blocking I/O operations
- Graceful shutdown with timeout

## Error Handling

- Failed log events don't block application
- Automatic reconnection for network handlers
- Fallback mechanisms for critical failures
- Detailed error reporting

## Best Practices

1. **Configuration**
   - Use appropriate log levels
   - Configure queue sizes based on load
   - Enable only needed handlers

2. **Usage**
   - Add context to log messages
   - Use structured logging
   - Include relevant metadata

3. **Monitoring**
   - Monitor queue sizes
   - Watch for dropped messages
   - Set up alerts for critical errors

## Dependencies

- structlog
- pydantic
- aiofiles
- sentry-sdk
- python-kafka
- aiohttp

## License

This module is part of the IDP Platform and follows its licensing terms. 

从多个维度对这个 logger 实现进行全面的审查和评估：

### 1. 架构设计 (9/10)

优点：
- ✅ 采用分层架构，关注点分离清晰（配置、处理器、管理器）
- ✅ 使用泛型和抽象基类实现优雅的处理器扩展机制
- ✅ 配置模型与处理器实现分离，便于维护和扩展

建议改进：
- 💡 可以考虑添加中间件层，支持日志事件的预处理和后处理
- 💡 可以引入处理器链（Chain of Responsibility）模式，支持更灵活的日志处理流程

### 2. 代码质量 (9/10)

优点：
- ✅ 完整的类型注解
- ✅ 清晰的文档字符串
- ✅ 一致的编码风格
- ✅ 合理的错误处理

建议改进：
- 💡 可以增加单元测试覆盖
- 💡 考虑添加性能基准测试

### 3. 功能完整性 (8/10)

优点：
- ✅ 支持主流日志输出目标
- ✅ 异步处理机制
- ✅ 配置验证
- ✅ 文件轮转

建议改进：
```python
# 1. 添加日志事件过滤器
class LogFilter:
    def filter(self, event_dict: Dict[str, Any]) -> bool:
        pass

# 2. 添加日志格式化器
class LogFormatter:
    def format(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        pass

# 3. 添加上下文管理
class LogContext:
    def __init__(self):
        self._context = {}

    def bind(self, **kwargs):
        self._context.update(kwargs)
```

### 4. 性能优化 (8/10)

优点：
- ✅ 异步队列处理
- ✅ 批处理支持
- ✅ 可配置的队列大小

建议改进：
```python
# 1. 添加内存缓冲池
class BufferPool:
    def __init__(self, size: int = 1000):
        self._pool = asyncio.Queue(maxsize=size)

# 2. 添加性能指标收集
class MetricsCollector:
    async def collect_metrics(self) -> Dict[str, Any]:
        return {
            "queue_size": self._queue.qsize(),
            "dropped_messages": self._dropped_count,
            "processed_messages": self._processed_count
        }
```

### 5. 错误处理 (8/10)

优点：
- ✅ 优雅的错误恢复
- ✅ 详细的错误日志
- ✅ 不影响主应用运行

建议改进：
```python
# 1. 添加重试机制
class RetryStrategy:
    async def retry(self, func, *args, max_retries: int = 3):
        for i in range(max_retries):
            try:
                return await func(*args)
            except Exception as e:
                if i == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** i)

# 2. 添加熔断机制
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5):
        self._failures = 0
        self._threshold = failure_threshold
```

### 6. 可维护性 (9/10)

优点：
- ✅ 模块化设计
- ✅ 清晰的文档
- ✅ 统一的配置管理

建议改进：
- 💡 添加更多的代码示例
- 💡 完善监控和诊断工具

### 7. 安全性 (7/10)

建议改进：
```python
# 1. 添加敏感信息过滤
class SensitiveDataFilter:
    def __init__(self, patterns: List[str]):
        self._patterns = patterns

    def filter(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # 过滤敏感信息
        return filtered_dict

# 2. 添加日志加密支持
class LogEncryption:
    def encrypt(self, data: str) -> str:
        pass

    def decrypt(self, data: str) -> str:
        pass
```

### 8. 可观测性 (7/10)

建议改进：
```python
# 1. 添加健康检查
class HealthCheck:
    async def check_health(self) -> Dict[str, str]:
        return {
            "status": "healthy",
            "queue_status": "normal",
            "processors": self._get_processor_status()
        }

# 2. 添加指标导出
class MetricsExporter:
    async def export_metrics(self) -> Dict[str, Any]:
        return {
            "throughput": self._calculate_throughput(),
            "latency": self._calculate_latency(),
            "error_rate": self._calculate_error_rate()
        }
```

### 总体评分：8.5/10

优秀的实现，主要优点：
1. 设计清晰，扩展性好
2. 性能考虑周到
3. 错误处理完善
4. 配置灵活

建议优先改进的方向：
1. 添加更完善的监控和可观测性支持
2. 增强安全性机制
3. 添加中间件支持
4. 完善测试覆盖

实施建议：
1. 首先实现监控和可观测性功能，这对生产环境至关重要
2. 其次添加安全相关功能
3. 最后实现中间件机制，提供更灵活的扩展点

你觉得这个评估如何？需要我详细解释某个方面吗？
