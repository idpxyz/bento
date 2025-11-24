"""
级联操作使用示例

展示如何使用 CascadeHelper 简化聚合级联操作

注意：这是一个示例文件，展示API用法，不是可运行的代码
"""


# ============ 使用示例说明 ============
#
# 步骤 1: 继承 CascadeMixin 和你的 Repository 基类
# 步骤 2: 在 __init__ 中定义 cascade_configs
# 步骤 3: 在 save() 方法中调用 save_with_cascade()
#
# ============ 代码示例 ============
#
# class OrderRepository(CascadeMixin, RepositoryAdapter):
#     """使用级联混入的 OrderRepository"""
#
#     def __init__(self, session: AsyncSession, mapper: Any, actor: str = "system") -> None:
#         super().__init__(repository=base_repo, mapper=mapper)
#         self.session = session
#         self.actor = actor
#
#         # 定义级联配置
#         self.cascade_configs: Dict[str, CascadeConfig] = {
#             "items": CascadeConfig(
#                 child_po_type=OrderItemPO,
#                 child_mapper=self.item_mapper.map,
#                 foreign_key_field="order_id"
#             )
#         }
#
#     async def save(self, order: Order) -> None:
#         """简化的保存方法"""
#         await self.save_with_cascade(order, self.cascade_configs)
#         await self.session.flush()
#
# ============ 优势 ============
#
# 1. 减少样板代码：无需手动删除和创建子实体
# 2. 类型安全：通过 CascadeConfig 提供配置
# 3. 统一处理：框架保证审计、拦截器等正确执行
# 4. 易于维护：级联逻辑集中在配置中


def example_usage_documentation() -> None:
    """
    使用文档函数（非可执行代码）

    完整示例请参考:
    applications/my-shop/contexts/ordering/infrastructure/repositories/
    """
    pass
