对于 PostgreSQL 数据库，一个完整且标准的 `database.yml` 配置文件应该包含以下关键部分：

```yaml:src/idp/framework/infrastructure/config/demo/config/database.yml
# PostgreSQL 数据库配置

# 默认环境配置
default:
  # 数据库类型
  type: "postgresql"
  
  # 连接配置
  connection:
    host: localhost
    port: 5432
    database: idp_default
    db_schema: public
    ssl_mode: "disable"           # 可选: disable, require, verify-ca, verify-full
    application_name: "idp_app"   # 在 pg_stat_activity 中显示的应用名称
  
  # 认证凭据
  credentials:
    username: postgres
    password: postgres
  
  # 连接池设置
  pool:
    min_size: 1                       # 最小连接数
    max_size: 10                      # 最大连接数 
    max_queries: 50000                # 每个连接最大查询数
    max_inactive_connection_lifetime: 300.0  # 不活跃连接的最大生命周期（秒）
    timeout: 30.0                     # 获取连接的超时时间（秒）
    recycle: 3600                     # 连接回收时间（秒）
    pre_ping: true                    # 是否在使用前进行连接检查
    echo: false                       # 是否打印SQL语句
  
  # 读写分离配置
  read_write:
    enable_read_write_split: false    # 是否启用读写分离
    read_write_ratio: 0.7             # 读写比例
    read_replicas: []                 # 读取副本列表
    auto_failover: true               # 是否自动故障转移
    failover_retry_interval: 5        # 故障转移重试间隔（秒）
  
  # 监控配置
  monitor:
    enable_metrics: true              # 是否启用指标收集
    metrics_interval: 60              # 指标收集间隔（秒）
    slow_query_threshold: 1.0         # 慢查询阈值（秒）
    enable_query_logging: true        # 是否启用查询日志
    log_slow_queries: true            # 是否记录慢查询
    log_queries: false                # 是否记录所有查询
  
  # 重试策略
  retry_attempts: 3                   # 连接失败重试次数
  retry_interval: 1.0                 # 重试间隔（秒）
  
  # 性能和安全配置
  statement_timeout: 30               # SQL语句超时时间（秒），null表示无限制
  enable_statement_cache: true        # 是否启用语句缓存
  statement_cache_size: 100           # 语句缓存大小
  keep_alive: true                    # 是否保持连接活跃
  
  # 其他应用级配置
  debug_sql: false                    # 是否记录SQL语句到日志
  enable_migration: true              # 是否启用数据库迁移
  migration_dir: "migrations"         # 迁移脚本目录

# 开发环境配置（继承默认配置，只覆盖差异部分）
dev:
  connection:
    database: idp_dev
    host: localhost
  credentials:
    password: dev_password
  pool:
    max_size: 5
  debug_sql: true
  monitor:
    enable_query_logging: true
    log_queries: true
  
# 测试环境配置
test:
  connection:
    database: idp_test
    host: localhost
  pool:
    max_size: 3
  retry_attempts: 2
  statement_timeout: 10
  
# 生产环境配置
prod:
  connection:
    host: db.production.example.com
    port: 5432
    database: idp_prod
    ssl_mode: "require"
  credentials:
    username: prod_user
    password: prod_secure_password
  pool:
    min_size: 5
    max_size: 20
    max_inactive_connection_lifetime: 600.0
  read_write:
    enable_read_write_split: true
    read_replicas:
      - host: read-replica-1.production.example.com
        port: 5432
        database: idp_prod
        username: prod_readonly
        password: prod_readonly_password
      - host: read-replica-2.production.example.com
        port: 5432
        database: idp_prod
        username: prod_readonly
        password: prod_readonly_password
  monitor:
    enable_metrics: true
    slow_query_threshold: 0.5
    log_slow_queries: true
  statement_timeout: 60
  debug_sql: false
```
## PostgreSQL 数据库配置文件详解

这个配置文件涵盖了数据库连接、性能优化和监控等各个方面的设置。以下是对各个配置部分的详细解释：

### 1. 基础配置

- **type**: 明确指定数据库类型为 `postgresql`，这对于支持多种数据库类型的系统很重要
- **connection**: 包含连接信息
  - `host`, `port`: 数据库服务器地址和端口
  - `database`: 要连接的数据库名称
  - `db_schema`: PostgreSQL 的 schema，默认为 "public"
  - `ssl_mode`: SSL 连接模式，支持 disable, require, verify-ca, verify-full
  - `application_name`: 在 PostgreSQL 服务器上标识应用程序的名称

- **credentials**: 数据库认证信息
  - `username`: 用户名
  - `password`: 密码

### 2. 连接池配置

`pool` 部分包含连接池的设置，这对于性能和资源管理非常重要：

- `min_size`: 池中保持的最小连接数
- `max_size`: 池中允许的最大连接数
- `max_queries`: 每个连接可以处理的最大查询数，达到此值后连接会被回收
- `max_inactive_connection_lifetime`: 非活跃连接的最大生命周期（秒）
- `timeout`: 从池中获取连接的超时时间
- `recycle`: 连接回收时间，超过此时间的连接会被重新创建
- `pre_ping`: 使用前检查连接是否有效
- `echo`: 是否打印执行的 SQL 语句，开发环境可设为 true

### 3. 读写分离配置

高性能应用常用的读写分离策略：

- `enable_read_write_split`: 是否启用读写分离
- `read_write_ratio`: 读写操作比例
- `read_replicas`: 只读副本列表，生产环境中配置了两个读副本
- `auto_failover`: 是否自动故障转移
- `failover_retry_interval`: 故障转移重试间隔

### 4. 监控配置

监控对于生产环境至关重要：

- `enable_metrics`: 是否启用指标收集
- `metrics_interval`: 指标收集间隔
- `slow_query_threshold`: 慢查询的时间阈值
- `enable_query_logging`: 是否启用查询日志
- `log_slow_queries`: 是否记录慢查询
- `log_queries`: 是否记录所有查询

### 5. 性能和安全配置

- `retry_attempts`: 连接失败重试次数
- `retry_interval`: 重试间隔
- `statement_timeout`: SQL 语句执行超时时间
- `enable_statement_cache`: 是否启用 SQL 语句缓存
- `statement_cache_size`: 语句缓存大小
- `keep_alive`: 是否维持连接活跃状态

### 环境特定配置

配置文件根据不同环境设置了不同的参数：

1. **开发环境 (dev)**:
   - 数据库名为 `idp_dev`
   - 启用了 SQL 调试
   - 连接池较小，适合开发使用
   - 启用全面查询日志记录

2. **测试环境 (test)**:
   - 更小的连接池
   - 更短的语句超时时间
   - 减少重试次数

3. **生产环境 (prod)**:
   - 使用更安全的 SSL 连接
   - 更大的连接池
   - 启用读写分离，配置多个读副本
   - 更严格的慢查询监控
   - 更长的语句超时时间

## 生产环境的高级特性

在生产环境中，我特别增加了几项重要特性：

1. **读写分离**:
   ```yaml
   read_write:
     enable_read_write_split: true
     read_replicas:
       - host: read-replica-1.production.example.com
         port: 5432
         database: idp_prod
         username: prod_readonly
         password: prod_readonly_password
       # 更多副本...
   ```

2. **更严格的监控**:
   ```yaml
   monitor:
     enable_metrics: true
     slow_query_threshold: 0.5  # 生产环境更严格的慢查询标准
     log_slow_queries: true
   ```

3. **更大的资源池**:
   ```yaml
   pool:
     min_size: 5
     max_size: 20
   ```

这个配置文件结构支持继承，每个环境只需指定与默认配置不同的参数，使配置文件更简洁易维护。通过这种结构化的配置，您可以轻松管理不同环境的数据库设置，并随时进行调整以满足性能和安全需求。
