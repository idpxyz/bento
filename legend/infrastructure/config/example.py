"""
配置系统使用示例

本示例展示了如何使用框架配置系统:
1. 初始化配置系统
2. 注册自定义配置模型和YAML配置
3. 访问配置
4. 调试配置来源
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from idp.framework.infrastructure.config import (
    config_manager,
    get_config,
    initialize,
    register_json_config,
    register_section,
    register_yaml_config,
)
from idp.framework.infrastructure.config.providers import EnvProvider

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用DEBUG级别以显示更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # 确保日志输出到标准输出
)
logger = logging.getLogger("config_example")

# 设置第三方库的日志级别为INFO，避免过多的调试信息
logging.getLogger("yaml").setLevel(logging.INFO)
logging.getLogger("pydantic").setLevel(logging.INFO)


# 演示：定义应用框架配置模型
class AppFrameworkConfig(BaseModel):
    """应用框架配置"""
    env: str = Field(default="dev", description="运行环境")
    debug: bool = Field(default=False, description="是否开启调试模式")
    app_name: str = Field(default="idp_app", description="应用名称")
    log_level: str = Field(default="INFO", description="日志级别")

    class Config:
        title = "应用框架配置"
        extra = "allow"


# 演示：定义应用特定的配置模型
class DatabaseConfig(BaseModel):
    """数据库配置"""
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(5432, description="数据库端口")
    database: str = Field(..., description="数据库名称")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    
    def get_connection_uri(self) -> str:
        """获取数据库连接URI"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


# 自定义环境变量提供器，专门用于数据库配置
class DatabaseEnvProvider(EnvProvider):
    """数据库环境变量配置提供器"""
    
    def __init__(self):
        super().__init__(namespace="database")
        self.source_tag = "ENV[数据库环境变量]"
        self.sources = {}  # 记录每个配置项的具体来源
    
    def _get_env_value(self, key: str, env_var: str, default_value: Any) -> Tuple[Any, str, bool]:
        """从环境变量获取值，并记录来源
        
        Args:
            key: 配置键名
            env_var: 环境变量名
            default_value: 默认值
            
        Returns:
            Tuple[Any, str, bool]: (值, 来源标记, 是否从环境变量获取)
        """
        value = os.environ.get(env_var)
        if value is not None:
            source = f"ENV[{env_var}]"
            # 对于端口，需要转换为整数
            if key == "port" and value.isdigit():
                return int(value), source, True
            return value, source, True
        else:
            return default_value, f"默认值[{default_value}]", False
    
    def load(self) -> dict:
        """从环境变量加载数据库配置"""
        if not self._loaded:
            self._load_env_file()
            self._loaded = True
        
        # 从环境变量构建数据库配置，并跟踪来源
        config = {}
        sources_info = {}
        self.has_real_env_values = {}  # 跟踪哪些配置项真正来自环境变量
        
        # 依次获取各个配置项，并记录其来源
        host, host_source, host_from_env = self._get_env_value("host", "DB_HOST", "localhost")
        config["host"] = host
        self.sources["host"] = host_source
        self.has_real_env_values["host"] = host_from_env
        
        port, port_source, port_from_env = self._get_env_value("port", "DB_PORT", 5432)
        config["port"] = port
        self.sources["port"] = port_source
        self.has_real_env_values["port"] = port_from_env
        
        name, name_source, name_from_env = self._get_env_value("name", "DB_NAME", "idp_dbs")
        config["name"] = name
        self.sources["name"] = name_source
        self.has_real_env_values["name"] = name_from_env
        
        user, user_source, user_from_env = self._get_env_value("user", "DB_USER", "postgres")
        config["user"] = user
        self.sources["user"] = user_source
        self.has_real_env_values["user"] = user_from_env
        
        password, password_source, password_from_env = self._get_env_value("password", "DB_PASSWORD", "postgres")
        config["password"] = password
        self.sources["password"] = password_source
        self.has_real_env_values["password"] = password_from_env
        
        # 生成来源信息字符串
        for key, value in config.items():
            sources_info[key] = f"{value} ({self.sources[key]})"
        
        # 记录环境变量来源
        logger.info(f"✅ [{self.source_tag}] 已加载数据库配置，带来源跟踪: {sources_info}")
        return config


# YAML基础提供器，用于处理嵌套结构的配置文件
class BaseYamlProvider(EnvProvider):
    """基础YAML配置提供器，处理嵌套结构的配置文件"""
    
    def __init__(self, namespace: str, file_path: str, env_name: str = "dev"):
        super().__init__(namespace=namespace)
        self.file_path = file_path
        self.env_name = env_name
        self.source_tag = f"YAML[{Path(file_path).name}:{env_name}]"
        self._data = {}
    
    def _extract_env_config(self, config: dict) -> dict:
        """从嵌套配置中提取环境特定的配置
        
        Args:
            config: 完整配置字典
            
        Returns:
            dict: 合并后的环境特定配置
        """
        logger.debug(f"🔍 提取环境配置 (环境:{self.env_name}), 原始配置: {config.keys()}")
        
        if not config:
            logger.warning("⚠️ 配置为空")
            return {}
            
        # 提取默认配置和环境特定配置
        default_config = config.get("default", {})
        env_config = config.get(self.env_name, {})
        
        logger.debug(f"📋 默认配置: {default_config}")
        logger.debug(f"📋 环境配置 ({self.env_name}): {env_config}")
        
        # 深度合并环境配置到默认配置
        result = {**default_config}
        
        # 如果有嵌套结构，需要递归合并
        for key, value in env_config.items():
            if isinstance(value, dict) and key in default_config and isinstance(default_config[key], dict):
                # 递归合并嵌套字典
                result[key] = {**default_config[key], **value}
                logger.debug(f"🔄 合并嵌套配置 '{key}': {result[key]}")
            else:
                # 直接覆盖
                result[key] = value
                logger.debug(f"✏️ 覆盖配置 '{key}': {value}")
        
        logger.debug(f"✅ 合并后的配置: {result}")
        return result
    
    def _map_to_flat_config(self, db_config: dict) -> dict:
        """将数据库配置映射到DatabaseConfig模型的格式
        
        Args:
            db_config: 原始数据库配置字典
            
        Returns:
            dict: 平铺后的数据库配置
        """
        logger.debug(f"🔍 映射配置到DatabaseConfig格式: {db_config}")
        
        # 确保配置包含connection部分
        if "connection" not in db_config:
            logger.warning(f"⚠️ 配置中缺少connection部分: {db_config}")
            connection = {}
        else:
            connection = db_config.get("connection", {})
            logger.debug(f"📋 连接配置: {connection}")
        
        # 映射到DatabaseConfig模型的格式
        result = {
            "host": connection.get("host", "localhost"),
            "port": connection.get("port", 5432),
            "name": connection.get("database", "idp_dev"),
            "user": connection.get("username", "postgres"),
            "password": connection.get("password", "postgres"),
        }
        
        logger.debug(f"✅ 映射后的配置: {result}")
        return result
    
    def load(self) -> dict:
        """加载YAML配置文件"""
        if not Path(self.file_path).exists():
            logger.warning(f"⚠️ 配置文件不存在: {self.file_path}")
            return {}
            
        import yaml
        try:
            logger.info(f"🔄 开始加载配置文件: {self.file_path}")
            with open(self.file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                logger.debug(f"📄 文件内容: \n{file_content[:500]}{'...' if len(file_content) > 500 else ''}")
                raw_config = yaml.safe_load(file_content) or {}
            
            logger.debug(f"📋 原始配置: {raw_config}")
            if not raw_config:
                logger.warning(f"⚠️ 配置文件为空或解析失败: {self.file_path}")
                return {}
            
            # 提取环境特定配置
            env_config = self._extract_env_config(raw_config)
            
            # 映射到模型格式
            if self.namespace == "database":
                self._data = self._map_to_flat_config(env_config)
                logger.info(f"✅ [{self.source_tag}] 已加载数据库配置: {self._data}")
            else:
                self._data = env_config
                logger.info(f"✅ [{self.source_tag}] 已加载配置: {self._data}")
                
            return self._data
        except Exception as e:
            logger.error(f"❌ [{self.source_tag}] 加载失败: {e}", exc_info=True)
            return {}


# YAML配置提供器，带源跟踪功能
class SourceTrackingYamlProvider(BaseYamlProvider):
    """带源跟踪的YAML配置提供器"""
    
    def __init__(self, namespace: str, file_path: str, env_name: str = "dev"):
        super().__init__(namespace=namespace, file_path=file_path, env_name=env_name)
        self.sources = {}  # 记录每个字段的来源
        
    def load(self) -> dict:
        """加载YAML配置并记录来源"""
        # 使用父类方法加载配置
        result = super().load()
        
        if result and self.namespace == "database":
            # 记录字段来源
            for key, value in result.items():
                self.sources[key] = f"{self.source_tag}"
                logger.debug(f"🏷️ 配置字段 '{key}' 来源: {self.source_tag}")
        
        return result


# JSON配置提供器，带源跟踪功能
class SourceTrackingJsonProvider(EnvProvider):
    """带源跟踪的JSON配置提供器"""
    
    def __init__(self, namespace: str, file_path: str):
        super().__init__(namespace=namespace)
        self.file_path = file_path
        self.source_tag = f"JSON[{Path(file_path).name}]"
        self._data = {}
        
    def load(self) -> dict:
        """加载JSON配置并记录来源"""
        if Path(self.file_path).exists():
            import json
            try:
                with open(self.file_path, 'r') as f:
                    self._data = json.load(f) or {}
                logger.info(f"📄 [{self.source_tag}] 已加载配置: {self._data}")
                return self._data
            except Exception as e:
                logger.error(f"❌ [{self.source_tag}] 加载失败: {e}")
        else:
            logger.warning(f"⚠️ 配置文件不存在: {self.file_path}")
        return {}


# 配置值跟踪器，用于记录每个配置项的来源
class ConfigSourceTracker:
    """配置来源跟踪器，记录每个配置项的具体来源"""
    
    def __init__(self):
        self.sources = {}  # 键: (配置名, 字段名) -> 值: 来源
        self.providers = {}  # 存储所有注册的提供器
        
    def register_provider(self, section: str, provider: Any, priority: int = 0):
        """注册配置提供器"""
        if section not in self.providers:
            self.providers[section] = []
        self.providers[section].append((provider, priority))
        # 按优先级排序，低优先级在前，高优先级在后（覆盖前者）
        self.providers[section].sort(key=lambda x: x[1])
    
    def track_config_loading(self, section: str):
        """追踪配置加载过程，记录每个字段的来源"""
        if section not in self.providers:
            logger.warning(f"⚠️ 配置段 {section} 没有注册提供器")
            return {}
            
        result = {}
        # 遍历所有注册的提供器，按优先级应用配置（低 -> 高）
        for provider, priority in self.providers[section]:
            config_data = provider._data if hasattr(provider, '_data') else provider.load()
            
            for key, value in config_data.items():
                should_apply = True
                
                # 处理环境变量提供器的特殊情况
                if (hasattr(provider, 'has_real_env_values') and 
                    key in provider.has_real_env_values and 
                    not provider.has_real_env_values[key]):
                    # 这是一个默认值，只在还没有配置时应用
                    should_apply = key not in result
                
                # 对于其他提供器，或者是真正的环境变量，总是应用（覆盖已有值）
                if should_apply:
                    # 应用此配置
                    result[key] = value
                    
                    # 记录配置来源
                    if hasattr(provider, 'sources') and key in provider.sources:
                        # 使用提供器自己的来源跟踪（如环境变量提供器）
                        self.sources[(section, key)] = provider.sources[key]
                    else:
                        # 使用提供器的通用标记
                        self.sources[(section, key)] = provider.source_tag
                        
        logger.info(f"🔍 配置段 [{section}] 源跟踪完成")
        return result
    
    def get_source(self, section: str, field: str) -> str:
        """获取配置项的来源"""
        return self.sources.get((section, field), "默认值")
    
    def print_source_report(self, section: str, config_obj: BaseModel):
        """打印配置项来源报告"""
        logger.info(f"\n===== {section} 配置来源报告 =====")
        for field, value in config_obj.model_dump().items():
            source = self.get_source(section, field)
            logger.info(f"{field}: {value} - 来源: {source}")


def create_debug_file(path: Path, content: Dict[str, Any]) -> None:
    """创建调试配置文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.suffix == '.yaml' or path.suffix == '.yml':
        import yaml
        with open(path, 'w') as f:
            yaml.dump(content, f)
        logger.info(f"📄 创建YAML配置文件: {path}")
    elif path.suffix == '.json':
        import json
        with open(path, 'w') as f:
            json.dump(content, f, indent=2)
        logger.info(f"📄 创建JSON配置文件: {path}")
    else:
        logger.error(f"❌ 不支持的文件格式: {path}")


def example_usage() -> None:
    """配置系统使用示例"""
    
    # 指向框架配置目录
    framework_config_dir = Path("/workspace/src/idp/framework/config")
    logger.info(f"框架配置目录: {framework_config_dir.absolute()}")
    
    # 验证配置目录是否存在
    if not framework_config_dir.exists():
        logger.error(f"❌ 配置目录不存在: {framework_config_dir}")
        return
    
    # 列出目录中的所有文件
    logger.info("📂 列出配置目录中的文件:")
    for file_path in framework_config_dir.glob("*"):
        if file_path.is_file():
            logger.info(f"  - {file_path.name} ({file_path.stat().st_size} 字节)")
    
    # 使用框架配置文件路径
    app_yaml_path = framework_config_dir / "app.yml"
    db_yaml_path = framework_config_dir / "database.yaml"
    
    # 详细检查文件存在
    logger.info(f"🔎 应用配置文件: {app_yaml_path} (存在: {app_yaml_path.exists()})")
    logger.info(f"🔎 数据库配置文件: {db_yaml_path} (存在: {db_yaml_path.exists()})")
    
    if db_yaml_path.exists():
        logger.info(f"📄 数据库配置文件大小: {db_yaml_path.stat().st_size} 字节")
        # 读取文件前100个字符以验证文件内容
        with open(db_yaml_path, 'r', encoding='utf-8') as f:
            preview = f.read(100)
            logger.info(f"📄 数据库配置文件预览: {preview}...")
    
    # 创建配置来源跟踪器
    source_tracker = ConfigSourceTracker()
    
    # 1. 注册应用特定的配置模型
    logger.info("🔧 注册应用框架配置模型")
    register_section("framework", AppFrameworkConfig)
    
    logger.info("🔧 注册数据库配置模型")
    register_section("database", DatabaseConfig)
    
    # 2. 创建带源跟踪的配置提供器
    # 应用框架配置提供器 (如果存在)
    if app_yaml_path.exists():
        app_yaml_provider = SourceTrackingYamlProvider("framework", str(app_yaml_path), env_name="dev")
        source_tracker.register_provider("framework", app_yaml_provider, priority=10)
        # 立即加载配置，确保数据已加载
        app_yaml_provider.load()
    
    # 数据库配置提供器
    logger.info(f"🔎 检查数据库配置文件: {db_yaml_path} (存在: {db_yaml_path.exists()})")
    db_yaml_provider = SourceTrackingYamlProvider("database", str(db_yaml_path), env_name="dev")
    db_env_provider = DatabaseEnvProvider()
    
    # 立即加载配置，确保数据已加载
    logger.info("🔄 预加载YAML配置")
    db_yaml_config = db_yaml_provider.load()  
    logger.info(f"🔎 预加载结果: {db_yaml_config}")
    
    # 3. 注册到源跟踪器 (优先级递增，高优先级会覆盖低优先级)
    # 对于数据库配置，优先级顺序: YAML -> 环境变量
    logger.info("🔧 注册提供器，优先级顺序: YAML配置 -> 环境变量")
    source_tracker.register_provider("database", db_yaml_provider, priority=10)
    source_tracker.register_provider("database", db_env_provider, priority=20)
    
    # 4. 跟踪配置加载过程
    logger.info("🔍 开始跟踪框架配置加载")
    app_config_data = source_tracker.track_config_loading("framework")
    
    logger.info("🔍 开始跟踪数据库配置加载")
    db_config_data = source_tracker.track_config_loading("database")
    
    logger.info(f"⭐ 应用配置跟踪结果: {app_config_data}")
    logger.info(f"⭐ 数据库配置跟踪结果: {db_config_data}")
    
    # 5. 注册到系统配置管理器
    logger.info("🔧 注册数据库YAML配置")
    
    # 创建自定义的YamlProvider
    from idp.framework.infrastructure.config.providers.yaml import YamlProvider
    
    class CustomYamlProvider(YamlProvider):
        """自定义YAML提供器，直接映射数据库配置"""
        
        def load(self) -> dict:
            yaml_data = super().load()
            if not yaml_data:
                return {}
                
            logger.debug(f"🔍 CustomYamlProvider 加载原始数据: {yaml_data}")
            
            # 如果是数据库配置，进行特殊处理
            if self.namespace == "database":
                # 提取默认配置和环境特定配置
                default_config = yaml_data.get("default", {})
                env_config = yaml_data.get("dev", {})
                
                # 合并配置
                merged_config = {**default_config}
                for key, value in env_config.items():
                    if isinstance(value, dict) and key in default_config and isinstance(default_config[key], dict):
                        merged_config[key] = {**default_config[key], **value}
                    else:
                        merged_config[key] = value
                
                # 提取connection部分
                connection = merged_config.get("connection", {})
                
                # 映射到所需格式
                result = {
                    "host": connection.get("host", "localhost"),
                    "port": connection.get("port", 5432),
                    "name": connection.get("database", "idp_dev"),
                    "user": connection.get("username", "postgres"),
                    "password": connection.get("password", "postgres"),
                }
                
                logger.debug(f"✅ CustomYamlProvider 映射结果: {result}")
                return result
            
            return yaml_data
    
    custom_yaml_provider = CustomYamlProvider("database", [str(db_yaml_path)], required=False)
    config_manager.register_provider(custom_yaml_provider)
    
    logger.info("🔧 注册数据库环境变量提供器")
    config_manager.register_provider(db_env_provider)
    
    # 6. 初始化配置系统
    try:
        logger.info("🚀 初始化配置系统")
        initialize(env_name="dev")
    except Exception as e:
        logger.error(f"❌ 初始化配置失败: {e}", exc_info=True)
        return
    
    # 7. 访问配置并生成来源报告
    try:
        # 获取框架配置
        framework_config = get_config("framework")
        logger.info("\n===== 框架配置加载结果 =====")
        logger.info(f"应用名称: {framework_config.app_name}")
        logger.info(f"环境: {framework_config.env}")
        logger.info(f"调试模式: {framework_config.debug}")
        logger.info(f"日志级别: {framework_config.log_level}")
        
        # 显示配置来源
        source_tracker.print_source_report("framework", framework_config)
        
        # 获取数据库配置
        try:
            db_config = get_config("database")
            logger.info("\n===== 数据库配置加载结果 =====")
            logger.info(f"主机: {db_config.host}")
            logger.info(f"端口: {db_config.port}")
            logger.info(f"数据库名: {db_config.name}")
            logger.info(f"用户名: {db_config.user}")
            logger.info(f"连接URI: {db_config.get_connection_uri()}")
            
            # 显示配置来源
            source_tracker.print_source_report("database", db_config)
            
        except Exception as e:
            logger.error(f"❌ 数据库配置未加载: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"❌ 配置访问失败: {e}", exc_info=True)
    
    # 8. 打印完整的配置源报告
    logger.info("\n📊 ===== 完整配置源报告 =====")
    for (section, field), source in source_tracker.sources.items():
        logger.info(f"{section}.{field} - 来源: {source}")


if __name__ == "__main__":
    example_usage() 