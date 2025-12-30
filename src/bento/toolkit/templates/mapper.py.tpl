"""{{Name}} 映射器接口"""
from typing import Protocol

from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
from contexts.{{context}}.infrastructure.models.{{name_lower}}_po import {{Name}}PO


class I{{Name}}Mapper(Protocol):
    """{{Name}} 映射器协议

    负责领域对象与持久化对象之间的双向映射。
    Infrastructure 层提供具体实现。
    """

    def to_po(self, domain_obj: {{Name}}) -> {{Name}}PO:
        """领域对象 -> 持久化对象"""
        ...

    def to_domain(self, po: {{Name}}PO) -> {{Name}}:
        """持久化对象 -> 领域对象"""
        ...


# ============================================================================
# 实现示例（使用 Bento Framework 的 AutoMapper）
# ============================================================================
#
# 创建文件：infrastructure/mappers/{{name_lower}}_mapper.py
#
# from bento.application.ports.mapper import AutoMapper
# from contexts.{{context}}.domain.model.{{name_lower}} import {{Name}}
# from contexts.{{context}}.infrastructure.models.{{name_lower}}_po import {{Name}}PO
#
# class {{Name}}Mapper(AutoMapper[{{Name}}, {{Name}}PO]):
#     """{{Name}} 映射器实现 - 使用框架 AutoMapper
#
#     Bento Framework 自动推断字段映射：
#     1. 同名字段自动映射（name -> name, price -> price）
#     2. ID 类型转换（ID ↔ str）
#     3. Enum 转换（Enum ↔ str/int）
#     4. 可选字段处理（Optional[T]）
#     5. 嵌套对象递归映射
#     6. 日期时间转换（datetime ↔ datetime）
#     7. Decimal 转换（Decimal ↔ Decimal）
#
#     使用方式：
#         # 领域对象 -> 持久化对象
#         po = mapper.to_po({{name_lower}})
#         
#         # 持久化对象 -> 领域对象
#         {{name_lower}} = mapper.to_domain(po)
#
#     自定义映射（如需要）：
#         def to_po(self, domain_obj: {{Name}}) -> {{Name}}PO:
#             # 自定义转换逻辑
#             po = super().to_po(domain_obj)
#             # 额外处理...
#             return po
#     """
#     pass
#
