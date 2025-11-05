"""应用层DTO基础类

提供所有DTO的基础功能和标准化配置。

设计目标：
- 统一DTO的基础行为
- 提供通用的序列化配置
- 确保数据验证的一致性
- 便于未来的功能扩展
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 泛型类型变量
T = TypeVar('T')


class BaseDTO(BaseModel):
    """应用层DTO基础类

    所有应用层DTO都应继承此类，获得：
    - 统一的序列化配置
    - 标准的验证行为
    - 通用的工具方法
    - 向前兼容的字段处理
    """

    model_config = ConfigDict(
        # 从ORM对象创建DTO时的配置
        from_attributes=True,

        # 验证赋值时的行为
        validate_assignment=True,

        # 允许使用枚举值
        use_enum_values=True,

        # 序列化时排除None值
        exclude_none=False,

        # 字符串自动去除首尾空白
        str_strip_whitespace=True,

        # 允许额外字段（向前兼容）
        extra='ignore'
    )

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """转换为字典格式

        Args:
            exclude_none: 是否排除None值

        Returns:
            字典格式的数据
        """
        return self.model_dump(exclude_none=exclude_none)

    def to_json(self, exclude_none: bool = True, indent: int = 2) -> str:
        """转换为JSON字符串

        Args:
            exclude_none: 是否排除None值
            indent: JSON缩进空格数

        Returns:
            JSON格式的字符串
        """
        return self.model_dump_json(exclude_none=exclude_none, indent=indent)

    @classmethod
    def create_from_dict(cls, data: Dict[str, Any]) -> "BaseDTO":
        """从字典创建DTO实例

        Args:
            data: 字典数据

        Returns:
            DTO实例
        """
        return cls.model_validate(data)

    @classmethod
    def create_from_json(cls, json_str: str) -> "BaseDTO":
        """从JSON字符串创建DTO实例

        Args:
            json_str: JSON字符串

        Returns:
            DTO实例
        """
        return cls.model_validate_json(json_str)

    def update_from_dict(self, data: Dict[str, Any]) -> "BaseDTO":
        """使用字典数据更新DTO

        Args:
            data: 更新数据

        Returns:
            更新后的DTO实例（新实例）
        """
        current_data = self.to_dict(exclude_none=False)
        current_data.update(data)
        return self.__class__.create_from_dict(current_data)

    def has_field(self, field_name: str) -> bool:
        """检查是否包含指定字段

        Args:
            field_name: 字段名

        Returns:
            是否包含该字段
        """
        return field_name in self.model_fields

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """安全获取字段值

        Args:
            field_name: 字段名
            default: 默认值

        Returns:
            字段值或默认值
        """
        return getattr(self, field_name, default)


class PaginatedResponseDTO(BaseModel, Generic[T]):
    """分页响应DTO基类"""
    total: int
    page: int
    size: int
    pages: int
    has_next: Optional[bool] = Field(None, description="是否有下一页")
    has_prev: Optional[bool] = Field(None, description="是否有上一页")
    # 可选的扩展元数据字段
    meta: Optional[Dict[str, Any]] = Field(None, description="扩展元数据，如统计信息等")
    items: List[T]

    @model_validator(mode="before")
    def compute_has_next_prev(cls, values):
        page = values.get('page', 1)
        pages = values.get('pages', 1)
        values['has_next'] = page < pages
        values['has_prev'] = page > 1
        return values
