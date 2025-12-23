"""Create order command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException
from bento.core.ids import ID

from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent as OrderCreated
from contexts.ordering.domain.models.order import Order


@dataclass
class OrderItemInput:
    """订单项输入"""

    product_id: str
    product_name: str
    quantity: int
    unit_price: float


@dataclass
class CreateOrderCommand:
    """Create order command."""

    customer_id: str
    items: list[OrderItemInput]


@command_handler
class CreateOrderHandler(CommandHandler[CreateOrderCommand, Order]):
    """Create order use case.

    创建订单并包含订单项。
    验证产品存在性（通过反腐败层与 Catalog BC 交互）。

    Architecture:
        - Application层协调跨BC业务流程
        - 通过 uow.port() 获取跨BC服务（Port/Adapter模式）
        - 依赖抽象接口（IProductCatalogService），不依赖具体实现
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateOrderCommand) -> None:
        """Validate command."""
        if not command.customer_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "customer_id", "reason": "cannot be empty"},
            )

        if not command.items:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "items", "reason": "order must have at least one item"},
            )

        # 验证每个订单项
        for idx, item in enumerate(command.items):
            if not item.product_id:
                raise ApplicationException(
                    reason_code="INVALID_PARAMS",
                    details={"field": f"items[{idx}].product_id", "reason": "cannot be empty"},
                )
            if item.quantity <= 0:
                raise ApplicationException(
                    reason_code="INVALID_PARAMS",
                    details={"field": f"items[{idx}].quantity", "reason": "must be greater than 0"},
                )
            if item.unit_price < 0:
                raise ApplicationException(
                    reason_code="INVALID_PARAMS",
                    details={"field": f"items[{idx}].unit_price", "reason": "cannot be negative"},
                )

    async def handle(self, command: CreateOrderCommand) -> Order:
        """Handle command execution."""
        # ✅ 通过 UoW Port 容器获取跨BC服务（运行时解析）
        from contexts.ordering.domain.ports.services.i_product_catalog_service import (
            IProductCatalogService,
        )

        product_catalog = self.uow.port(IProductCatalogService)

        # ✅ 通过反腐败层验证产品存在性（不直接依赖 Catalog BC）
        product_ids = [item.product_id for item in command.items]
        _, unavailable_ids = await product_catalog.check_products_available(product_ids)

        if unavailable_ids:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={
                    "resource": "product",
                    "unavailable_products": unavailable_ids,
                    "message": f"Products not found or unavailable: {', '.join(unavailable_ids)}",
                },
            )

        # TODO P2: 检查库存充足（需要在 IProductCatalogService 中添加方法）
        # products_info = await self._product_catalog.get_products_info(product_ids)
        # for item in command.items:
        #     product_info = products_info[item.product_id]
        #     if product_info.stock < item.quantity:
        #         raise ApplicationException(...)

        # 创建订单聚合根
        order_id = ID.generate()  # 生成 ID 对象（不转字符串）
        order = Order(
            id=order_id,  # 传递 ID 对象
            customer_id=command.customer_id,
            items=[],  # 先创建空订单
        )

        # 添加订单项（使用领域方法）
        for item_input in command.items:
            order.add_item(
                product_id=item_input.product_id,
                product_name=item_input.product_name,
                quantity=item_input.quantity,
                unit_price=item_input.unit_price,
            )

        # 发布领域事件（包含完整订单信息）
        order.add_event(
            OrderCreated(
                # 事件元数据
                aggregate_id=order.id,  # ✅ 直接传递 ID 对象
                tenant_id="default",  # ✅ 设置租户ID（多租户支持）
                # 订单基本信息
                order_id=order.id,  # ✅ 直接传递 ID 对象
                customer_id=order.customer_id,
                total=order.total,
                item_count=len(order.items),
                # ✅ 订单项详情 - 下游服务可以立即处理
                items=[
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "subtotal": item.subtotal,
                    }
                    for item in order.items
                ],
            )
        )

        # 持久化订单（Repository 会自动 track）
        order_repo = self.uow.repository(Order)
        await order_repo.save(order)
        # ✅ No need to manually track - repository handles it automatically

        return order
