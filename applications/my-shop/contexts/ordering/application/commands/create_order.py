"""Create order command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent as OrderCreated
from contexts.ordering.domain.order import Order


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


class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, Order]):
    """Create order use case.

    创建订单并包含订单项。
    验证产品存在性（与 Product 聚合交互）。
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateOrderCommand) -> None:
        """Validate command."""
        if not command.customer_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "customer_id", "reason": "cannot be empty"},
            )

        if not command.items:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "items", "reason": "order must have at least one item"},
            )

        # 验证每个订单项
        for idx, item in enumerate(command.items):
            if not item.product_id:
                raise ApplicationException(
                    error_code=CommonErrors.INVALID_PARAMS,
                    details={"field": f"items[{idx}].product_id", "reason": "cannot be empty"},
                )
            if item.quantity <= 0:
                raise ApplicationException(
                    error_code=CommonErrors.INVALID_PARAMS,
                    details={"field": f"items[{idx}].quantity", "reason": "must be greater than 0"},
                )
            if item.unit_price < 0:
                raise ApplicationException(
                    error_code=CommonErrors.INVALID_PARAMS,
                    details={"field": f"items[{idx}].unit_price", "reason": "cannot be negative"},
                )

    async def handle(self, command: CreateOrderCommand) -> Order:
        """Handle command execution."""
        # Validate products exist using UoW's repository
        from contexts.catalog.domain.product import Product

        product_repo = self.uow.repository(Product)

        for item in command.items:
            product = await product_repo.get(item.product_id)  # type: ignore
            if not product:
                raise ApplicationException(
                    error_code=CommonErrors.NOT_FOUND,
                    details={"resource": "product", "id": item.product_id},
                )
            # TODO P2: 检查库存充足
            # if product.stock < item.quantity:
            #     raise ApplicationException(...)

        # 创建订单聚合根
        order_id = str(ID.generate())
        order = Order(
            id=order_id,
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
                aggregate_id=order.id,  # ✅ 设置聚合根ID
                tenant_id="default",  # ✅ 设置租户ID（多租户支持）
                # 订单基本信息
                order_id=order.id,
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
