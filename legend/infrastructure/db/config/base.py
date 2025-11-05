"""数据库配置模块"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class ConnectionConfig(BaseModel):
    """数据库连接配置"""
    host: str = Field(..., description="数据库主机")
    port: int = Field(..., description="数据库端口")
    database: str = Field(..., description="数据库名称")
    db_schema: Optional[str] = Field(default=None, description="数据库schema")
    ssl_mode: Optional[str] = Field(
        None,
        description="SSL模式",
        json_schema_extra={
            "enum": ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]}
    )
    connect_timeout: Optional[float] = Field(
        default=30.0, description="连接超时时间(秒)")
    application_name: Optional[str] = Field(
        default=None, description="应用名称，用于在数据库监控中标识连接")


class CredentialsConfig(BaseModel):
    """数据库凭证配置"""
    username: str = Field(..., description="数据库用户名")
    password: str = Field(
        ...,
        description="数据库密码",
        min_length=1  # 最小密码长度
    )

    def __repr__(self):
        """重写repr方法以保护敏感信息"""
        return f"CredentialsConfig(username='{self.username}', password='****')"


class PoolConfig(BaseModel):
    """连接池配置"""
    min_size: int = Field(default=5, description="最小连接数")
    max_size: int = Field(default=20, description="最大连接数")
    max_overflow: int = Field(default=10, description="最大溢出连接数")
    timeout: float = Field(default=30.0, description="连接获取超时时间(秒)")
    recycle: int = Field(default=3600, description="连接回收时间(秒)")
    pre_ping: bool = Field(default=True, description="是否启用连接预检")
    echo: bool = Field(default=False, description="是否打印SQL语句")


class ReadReplicaConfig(BaseModel):
    """只读副本连接配置"""
    connection: ConnectionConfig = Field(..., description="副本连接配置")
    credentials: CredentialsConfig = Field(..., description="副本凭证配置")

    def get_url(self) -> str:
        """获取数据库连接URL

        Returns:
            str: 数据库连接URL
        """
        # 构建基本 URL
        url = f"postgresql+asyncpg://{self.credentials.username}:{self.credentials.password}@{self.connection.host}:{self.connection.port}/{self.connection.database}"

        return url

    def get_connect_args(self) -> Dict[str, Any]:
        """获取连接参数

        Returns:
            Dict[str, Any]: 连接参数
        """
        connect_args = {}

        # 如果有 schema，添加到连接参数中
        if self.connection.db_schema:
            # 使用 server_settings 来设置 search_path
            connect_args["server_settings"] = {
                "search_path": self.connection.db_schema
            }

        return connect_args


class ReadWriteConfig(BaseModel):
    """读写分离配置"""
    enable_read_write_split: bool = Field(
        default=False, description="是否启用读写分离")
    read_write_ratio: float = Field(default=0.7, description="读写比例")
    read_replicas: List[ReadReplicaConfig] = Field(
        default_factory=list, description="只读副本配置列表")
    auto_failover: bool = Field(default=True, description="是否自动故障转移")
    failover_retry_interval: int = Field(default=5, description="故障转移重试间隔(秒)")
    max_failover_attempts: int = Field(default=3, description="最大故障转移次数")
    load_balance_strategy: str = Field(
        default="round_robin",
        description="负载均衡策略",
        json_schema_extra={"choices": [
            "round_robin", "random", "least_connections"]}
    )
    health_check_interval: int = Field(
        default=30,
        description="健康检查间隔(秒)"
    )

    def get_replica_uris(self) -> List[str]:
        """获取副本连接URI列表"""
        uris = []
        for replica in self.read_write.read_replicas:
            # 根据数据库类型构建URI
            if self.type.lower() == "mysql":
                uri = f"mysql+aiomysql://{replica.credentials.username}:{replica.credentials.password}@{replica.connection.host}:{replica.connection.port}/{replica.connection.database}"
            elif self.type.lower() == "postgresql":
                uri = f"postgresql+asyncpg://{replica.credentials.username}:{replica.credentials.password}@{replica.connection.host}:{replica.connection.port}/{replica.connection.database}"
            elif self.type.lower() == "sqlite":
                uri = f"sqlite+aiosqlite:///{replica.connection.database}"
            uris.append(uri)
        return uris


class DatabaseConfig(BaseModel):
    """数据库配置"""
    type: DatabaseType = Field(..., description="数据库类型")
    connection: ConnectionConfig = Field(..., description="主数据库连接配置")
    credentials: CredentialsConfig = Field(..., description="数据库凭证配置")
    pool: PoolConfig = Field(default_factory=PoolConfig, description="连接池配置")
    read_write: ReadWriteConfig = Field(
        default_factory=ReadWriteConfig, description="读写分离配置")
    retry_attempts: int = Field(default=3, description="重试次数")
    retry_interval: float = Field(default=1.0, description="重试间隔(秒)")
    statement_timeout: Optional[float] = Field(
        default=None, description="语句超时时间(秒)")
    enable_statement_cache: bool = Field(default=True, description="是否启用语句缓存")
    statement_cache_size: int = Field(default=100, description="语句缓存大小")
    keep_alive: bool = Field(default=False, description="是否保持连接")
    enable_draining: bool = Field(default=True, description="是否启用连接耗尽")
    draining_timeout: float = Field(default=30.0, description="连接耗尽超时时间(秒)")
    draining_mode: str = Field(
        default="graceful",
        description="连接耗尽模式",
        json_schema_extra={"enum": ["graceful", "immediate", "force"]}
    )

    # 使用 ConfigDict 替代 class Config
    model_config = ConfigDict(
        # 使连接配置更灵活，允许额外字段
        extra="allow"
    )

    def get_connection_uri(self) -> str:
        """获取数据库连接URI，基于基本配置"""
        # 根据数据库类型选择不同的URI格式
        if self.type.lower() == "mysql":
            return f"mysql+aiomysql://{self.credentials.username}:{self.credentials.password}@{self.connection.host}:{self.connection.port}/{self.connection.database}"
        elif self.type.lower() == "sqlite":
            return f"sqlite+aiosqlite:///{self.connection.database}"
        else:  # postgresql 或其他
            return f"postgresql+asyncpg://{self.credentials.username}:{self.credentials.password}@{self.connection.host}:{self.connection.port}/{self.connection.database}"

    def __hash__(self) -> int:
        """使对象可哈希，用于字典键和集合元素

        基于类型、连接信息和凭据信息的组合哈希值

        Returns:
            int: 哈希值
        """
        return hash((
            self.type,
            self.connection.host,
            self.connection.port,
            self.connection.database,
            self.credentials.username
        ))

    def __eq__(self, other) -> bool:
        """比较两个配置是否相等

        对比关键属性以确定两个数据库配置是否等价

        Args:
            other: 要比较的对象

        Returns:
            bool: 是否相等
        """
        if not isinstance(other, DatabaseConfig):
            return False

        return (
            self.type == other.type and
            self.connection.host == other.connection.host and
            self.connection.port == other.connection.port and
            self.connection.database == other.connection.database and
            self.credentials.username == other.credentials.username
        )
