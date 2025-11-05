from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)


class ConfigurationError(Exception):
    """配置异常基类"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """无效配置异常"""

    def __init__(self, message: str, errors: Optional[list] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """格式化错误信息"""
        if not self.errors:
            return self.message

        error_messages = [self.message, "\n验证错误详情:"]

        for i, error in enumerate(self.errors, 1):
            loc = ".".join(str(l) for l in error.get("loc", []))
            msg = error.get("msg", "未知错误")
            typ = error.get("type", "未知类型")
            error_messages.append(f"  {i}. 字段: {loc}, 错误: {msg} [{typ}]")

        return "\n".join(error_messages)


def format_pydantic_errors(errors: list) -> list:
    """将Pydantic验证错误转换为标准格式
    
    Args:
        errors: Pydantic错误列表
        
    Returns:
        list: 标准格式的错误列表
    """
    formatted_errors = []

    for error in errors:
        formatted_errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })

    return formatted_errors


class ConfigSource(ABC):
    """配置源抽象基类"""

    @abstractmethod
    def load(self, key: str) -> Dict[str, Any]:
        """从配置源加载指定键的配置
        
        Args:
            key: 配置键名
            
        Returns:
            Dict[str, Any]: 配置数据字典
            
        Raises:
            ConfigurationError: 配置加载错误
        """
        pass


class ConfigSection(Generic[T]):
    """配置项管理类，支持类型验证"""

    def __init__(self, schema_class: Type[T], config_data: Optional[Dict[str, Any]] = None):
        """
        初始化配置项
        
        Args:
            schema_class: Pydantic模型类，用于验证配置
            config_data: 初始配置数据
        """
        self.schema_class = schema_class
        self._instance: Optional[T] = None
        self._raw_data: Dict[str, Any] = {}  # 存储原始配置数据
        if config_data:
            self.update(config_data)

    def update(self, config_data: Dict[str, Any]) -> T:
        """更新配置数据
        
        Args:
            config_data: 新的配置数据
            
        Returns:
            T: 更新后的配置实例
        """
        self._raw_data = config_data
        try:
            self._instance = self.schema_class(**self._raw_data)
            return self._instance
        except ValidationError as e:
            error_list = e.errors(include_url=False)

            # 获取模型名称
            model_name = self.schema_class.__name__

            # 创建更友好的错误消息
            error_message = f"配置验证失败：'{model_name}' 模型验证出现 {len(error_list)} 个错误"

            # 根据错误类型提供解决方案建议
            missing_fields = [error["loc"][0] for error in error_list if error["type"] == "missing"]
            if missing_fields:
                error_message += f"\n缺少必填字段: {', '.join(missing_fields)}"
                error_message += "\n请检查配置文件格式或环境变量是否正确提供了这些字段"

            # 创建格式化的错误
            formatted_errors = format_pydantic_errors(error_list)

            # 抛出自定义错误
            raise InvalidConfigurationError(error_message, formatted_errors)
        except Exception as e:
            # 其他类型的错误
            raise ConfigurationError(f"配置更新失败: {e}")

    def get(self) -> T:
        """获取配置实例
        
        Returns:
            T: 配置实例
            
        Raises:
            ConfigurationError: 如果配置未初始化
        """
        if self._instance is None:
            raise ConfigurationError("配置未初始化")
        return self._instance

    def get_raw_data(self) -> Dict[str, Any]:
        """获取原始配置数据
        
        Returns:
            Dict[str, Any]: 原始配置数据
        """
        return self._raw_data
