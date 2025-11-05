"""
环境变量配置示例

本示例展示了如何从环境变量加载数据库配置
"""

import os

from pydantic import BaseModel, Field

from idp.framework.infrastructure.config import (
    config_manager,
    get_config,
    initialize,
    register_section,
)
from idp.framework.infrastructure.config.providers import EnvProvider


class DatabaseEnvConfig(BaseModel):
    """从环境变量加载的数据库配置"""
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(5432, description="数据库端口")
    name: str = Field(..., description="数据库名称")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    
    # 可选的只读数据库配置
    read_host: str = Field("", description="只读数据库主机地址")
    read_port: int = Field(5432, description="只读数据库端口")
    read_name: str = Field("", description="只读数据库名称")
    read_user: str = Field("", description="只读数据库用户名")
    read_password: str = Field("", description="只读数据库密码")
    
    def get_connection_uri(self) -> str:
        """获取主数据库连接URI"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def get_read_connection_uri(self) -> str:
        """获取只读数据库连接URI，如果配置了的话"""
        if not self.read_host or not self.read_name:
            return ""
        return f"postgresql://{self.read_user}:{self.read_password}@{self.read_host}:{self.read_port}/{self.read_name}"
    
    def has_read_replica(self) -> bool:
        """检查是否配置了只读副本"""
        return bool(self.read_host and self.read_name)


class DatabaseEnvProvider(EnvProvider):
    """数据库环境变量配置提供器"""
    
    def __init__(self):
        super().__init__(namespace="database")
    
    def load(self) -> dict:
        """从环境变量加载数据库配置"""
        if not self._loaded:
            self._load_env_file()
            self._loaded = True
        
        # 从环境变量构建数据库配置
        config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "postgres"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
            
            # 可选的只读数据库配置
            "read_host": os.getenv("DB_READ_HOST", ""),
            "read_port": int(os.getenv("DB_READ_PORT", "5432")),
            "read_name": os.getenv("DB_READ_NAME", ""),
            "read_user": os.getenv("DB_READ_USER", ""),
            "read_password": os.getenv("DB_READ_PASSWORD", ""),
        }
        
        return config


def example_env_usage() -> None:
    """环境变量配置示例"""
    
    # 1. 注册数据库配置模型
    register_section("database", DatabaseEnvConfig)
    
    # 2. 注册数据库环境变量提供器
    db_env_provider = DatabaseEnvProvider()
    config_manager.register_provider(db_env_provider)
    
    # 3. 初始化配置系统
    initialize(env_name="dev")
    
    # 4. 使用配置
    try:
        # 获取数据库配置
        db_config = get_config("database")
        print(f"数据库连接: {db_config.get_connection_uri()}")
        
        # 检查是否配置了只读副本
        if db_config.has_read_replica():
            print(f"只读数据库连接: {db_config.get_read_connection_uri()}")
        else:
            print("未配置只读数据库")
            
    except Exception as e:
        print(f"配置访问失败: {e}")


if __name__ == "__main__":
    example_env_usage() 