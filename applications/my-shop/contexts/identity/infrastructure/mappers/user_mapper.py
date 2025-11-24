"""User Mapper - 使用 Bento Framework 的 AutoMapper

AutoMapper 提供零配置的自动映射：
1. 自动分析 User 和 UserPO 的字段类型
2. 自动推断转换规则（ID、Enum、简单类型）
3. 自动处理 Optional 字段
4. 减少 90%+ 的样板代码
"""

from bento.application.mapper import AutoMapper

from contexts.identity.domain.models.user import User
from contexts.identity.infrastructure.models.user_po import UserPO


class UserMapper(AutoMapper[User, UserPO]):
    """
    User Mapper - 使用 Bento 的 AutoMapper

    零配置自动映射：
    - User.id ↔ UserPO.id (自动)
    - User.name ↔ UserPO.name (自动)
    - User.email ↔ UserPO.email (自动)

    审计字段：
    - UserPO 的 created_at, updated_at, created_by, updated_by, version
    - 由 AuditInterceptor 和 OptimisticLockInterceptor 自动处理
    - Mapper 不需要关心这些字段

    框架自动提供：
    - map(domain_obj) -> po_obj  (AR -> PO)
    - map_reverse(po_obj) -> domain_obj  (PO -> AR)
    - map_list(domain_objects) -> list[po_obj]
    - map_reverse_list(pos) -> list[domain_obj]

    如果需要自定义某个字段的转换，可以使用：
    - self.override_field("field_name", to_po=..., from_po=...)
    - self.alias_field("domain_field", "po_field")
    - self.ignore_fields("field1", "field2")
    """

    def __init__(self):
        """
        初始化 AutoMapper

        传入 Domain 类型和 PO 类型，框架会自动分析并生成映射逻辑。
        """
        super().__init__(
            domain_type=User,
            po_type=UserPO,
            # 可选配置：
            # include_none=False,  # 是否映射 None 值
            # strict=False,  # 严格模式（未映射的字段会报错）
            # debug=False,  # 调试模式（打印映射日志）
        )

        # 忽略 PO 的审计和元数据字段（它们由 Interceptor 处理）
        # AutoMapper 会自动忽略 Domain 中不存在的字段，所以这一步是可选的
        # self.ignore_fields(
        #     "created_at",
        #     "created_by",
        #     "updated_at",
        #     "updated_by",
        #     "version",
        #     "deleted_at",
        #     "deleted_by",
        # )

        # 如果需要自定义某个字段的转换，可以这样做：
        # self.override_field(
        #     "email",
        #     to_po=lambda email: email.lower(),  # 存储时转小写
        #     from_po=lambda email: email.lower()  # 读取时保持小写
        # )

    # 不需要实现 map() 和 map_reverse() 方法！
    # AutoMapper 会根据类型分析自动生成这些方法
    #
    # 如果确实需要完全自定义映射逻辑，可以重写：
    # def map(self, domain_obj: User) -> UserPO:
    #     # 自定义 AR -> PO 逻辑
    #     pass
    #
    # def map_reverse(self, po: UserPO) -> User:
    #     # 自定义 PO -> AR 逻辑
    #     pass
