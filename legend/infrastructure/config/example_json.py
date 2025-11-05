"""
JSON配置示例

本示例展示了如何使用JSON格式的配置文件
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field

from idp.framework.infrastructure.config import (
    get_config,
    initialize,
    register_json_config,
    register_section,
)


class DatabaseJsonConfig(BaseModel):
    """数据库配置（从JSON加载）"""
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(5432, description="数据库端口")
    name: str = Field(..., description="数据库名称")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    
    # 连接池配置
    pool: dict = Field(default_factory=dict, description="连接池配置")
    
    # 读写分离配置
    read_write: dict = Field(default_factory=dict, description="读写分离配置")
    
    # 监控配置
    monitoring: dict = Field(default_factory=dict, description="监控配置")
    
    def get_connection_uri(self) -> str:
        """获取数据库连接URI"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def get_pool_size(self) -> tuple:
        """获取连接池大小配置"""
        min_size = self.pool.get("min_size", 5)
        max_size = self.pool.get("max_size", 20)
        return min_size, max_size
    
    def is_read_write_split_enabled(self) -> bool:
        """检查是否启用读写分离"""
        return self.read_write.get("enable_read_write_split", False)


def example_json_usage() -> None:
    """JSON配置使用示例"""
    
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    
    # 配置文件路径
    json_file_path = current_dir / "example_config" / "database.json"
    
    # 检查文件是否存在
    if not json_file_path.exists():
        print(f"错误: 配置文件不存在: {json_file_path}")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"尝试查找文件...")
        possible_paths = list(Path('.').glob('**/database.json'))
        if possible_paths:
            print(f"找到可能的配置文件: {possible_paths}")
            json_file_path = possible_paths[0]
            print(f"使用文件: {json_file_path}")
        else:
            print("未找到database.json文件")
            return
    
    # 将路径转换为绝对路径的字符串
    json_file_path_str = str(json_file_path.absolute())
    print(f"使用配置文件: {json_file_path_str}")
    
    # 1. 注册配置模型
    register_section("database", DatabaseJsonConfig)
    
    # 2. 注册JSON配置文件
    register_json_config(
        namespace="database",
        file_paths=[json_file_path_str],
        required=False  # 改为False，这样即使文件不存在也不会直接报错
    )
    
    # 3. 初始化配置系统
    try:
        initialize()
    except Exception as e:
        print(f"初始化配置失败: {e}")
        return
    
    # 4. 使用配置
    try:
        # 获取数据库配置
        db_config = get_config("database")
        print("\n===== 数据库配置 (从JSON加载) =====")
        print(f"连接URI: {db_config.get_connection_uri()}")
        
        # 访问嵌套配置
        min_size, max_size = db_config.get_pool_size()
        print(f"连接池大小: {min_size}-{max_size}")
        
        if db_config.is_read_write_split_enabled():
            print("已启用读写分离")
        else:
            print("未启用读写分离")
            
        # 监控配置
        if db_config.monitoring.get("enable_metrics", False):
            print(f"已启用指标收集，间隔: {db_config.monitoring.get('metrics_interval')}秒")
            
    except Exception as e:
        print(f"配置访问失败: {e}")


if __name__ == "__main__":
    example_json_usage() 