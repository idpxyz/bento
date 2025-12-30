"""Order Projection - P3 高级特性：将写模型投影到读模型"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from bento.domain.domain_event import DomainEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent
from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent
from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO
from contexts.ordering.infrastructure.models.read_models.order_read_model import (
    OrderReadModel,
)

T = TypeVar("T", bound=DomainEvent)


def handles_event(
    event_type: type[T],
) -> Callable[[Callable[[Any, T], Any]], Callable[[Any, DomainEvent], Any]]:
    """Decorator to handle specific event types in a type-safe way."""

    def decorator(handler: Callable[[Any, T], Any]) -> Callable[[Any, DomainEvent], Any]:
        @wraps(handler)
        async def wrapper(self: Any, event: DomainEvent) -> None:
            # First check if the event is an instance of the expected type
            if not isinstance(event, event_type):
                # If not, check if the event has a topic that matches the expected type's topic
                expected_topic = getattr(event_type, "topic", None)
                actual_topic = getattr(event, "topic", None)

                if expected_topic is None or actual_topic != expected_topic:
                    raise TypeError(
                        f"Expected {event_type.__name__} or topic '{expected_topic}', "
                        f"got {type(event).__name__} with topic '{actual_topic}'"
                    )

                # If we get here, the topics match, so we can safely cast
                event = cast(T, event)
            return await handler(self, event)

        return wrapper

    return decorator


class OrderProjection:
    """将写模型投影到读模型

    P3 高级特性：CQRS 投影

    职责：
    - 监听领域事件
    - 更新读模型
    - 保持数据同步
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @handles_event(OrderCreatedEvent)
    async def handle_order_created(self, event: OrderCreatedEvent) -> None:
        """订单创建事件 → 创建读模型

        Args:
            event: OrderCreated 事件
        """
        logger = logging.getLogger(__name__)
        logger.info(f"[OrderProjection] Handling OrderCreatedEvent for order_id: {event.order_id}")

        # 1. 从写模型获取数据
        try:
            result = await self.session.execute(select(OrderPO).where(OrderPO.id == event.order_id))
            order_po = result.scalar_one_or_none()
            logger.info(f"[OrderProjection] Retrieved OrderPO: {order_po}")

            if not order_po:
                logger.warning(
                    f"[OrderProjection] OrderPO not found for order_id: {event.order_id}"
                )
                return

            # 2. 获取订单项
            result = await self.session.execute(
                select(OrderItemPO).where(OrderItemPO.order_id == event.order_id)
            )
            item_pos = result.scalars().all()
            logger.info(
                f"[OrderProjection] Retrieved {len(item_pos)} OrderItemPOs for order_id: {event.order_id}"
            )

            # 3. 计算衍生字段
            total_amount = sum(item.quantity * item.unit_price for item in item_pos)
            items_count = len(item_pos)
            logger.info(
                f"[OrderProjection] Calculated total_amount: {total_amount}, items_count: {items_count}"
            )

            # 4. 创建读模型
            read_model = OrderReadModel(
                id=order_po.id,
                customer_id=order_po.customer_id,
                status=order_po.status,
                total_amount=total_amount,  # 预计算
                items_count=items_count,  # 预计算
                created_at=order_po.created_at,
                paid_at=order_po.paid_at,
                shipped_at=order_po.shipped_at,
            )
            logger.info(f"[OrderProjection] Created OrderReadModel: {read_model.__dict__}")

            try:
                self.session.add(read_model)
                await self.session.commit()
                logger.info("[OrderProjection] Successfully committed OrderReadModel to database")
            except Exception as e:
                logger.error(f"[OrderProjection] Error committing OrderReadModel: {str(e)}")
                await self.session.rollback()
                raise
        except Exception as e:
            logger.error(
                f"[OrderProjection] Unexpected error in handle_order_created: {str(e)}",
                exc_info=True,
            )
            raise

    @handles_event(OrderPaidEvent)
    async def handle_order_paid(self, event: OrderPaidEvent) -> None:
        """订单支付事件 → 更新读模型

        Args:
            event: OrderPaid 事件
        """
        logger = logging.getLogger(__name__)
        logger.info(f"[OrderProjection] Handling OrderPaidEvent for order_id: {event.order_id}")

        try:
            result = await self.session.execute(
                select(OrderReadModel).where(OrderReadModel.id == event.order_id)
            )
            read_model = result.scalar_one_or_none()

            if read_model:
                logger.info(f"[OrderProjection] Updating OrderReadModel: {event.order_id} to paid")
                read_model.status = "paid"

                # 确保 paid_at 是 datetime 对象
                paid_at = event.paid_at
                if isinstance(paid_at, str):
                    from datetime import datetime

                    paid_at = datetime.fromisoformat(paid_at.replace("Z", "+00:00"))

                read_model.paid_at = paid_at

                await self.session.commit()
                logger.info(
                    f"[OrderProjection] Successfully updated OrderReadModel: {event.order_id}"
                )
            else:
                logger.warning(
                    f"[OrderProjection] OrderReadModel not found for order_id: {event.order_id}"
                )
        except Exception as e:
            logger.error(
                f"[OrderProjection] Error updating OrderReadModel for order {event.order_id}: {str(e)}",
                exc_info=True,
            )
            await self.session.rollback()
            raise

    @handles_event(OrderShippedEvent)
    async def handle_order_shipped(self, event: OrderShippedEvent) -> None:
        """订单发货事件 → 更新读模型

        Args:
            event: OrderShipped 事件
        """
        logger = logging.getLogger(__name__)
        logger.info(f"[OrderProjection] Handling OrderShippedEvent for order_id: {event.order_id}")

        try:
            result = await self.session.execute(
                select(OrderReadModel).where(OrderReadModel.id == event.order_id)
            )
            read_model = result.scalar_one_or_none()

            if read_model:
                logger.info(
                    f"[OrderProjection] Updating OrderReadModel: {event.order_id} to shipped"
                )
                read_model.status = "shipped"

                # 确保 shipped_at 是 datetime 对象
                shipped_at = event.shipped_at
                if isinstance(shipped_at, str):
                    from datetime import datetime

                    shipped_at = datetime.fromisoformat(shipped_at.replace("Z", "+00:00"))

                read_model.shipped_at = shipped_at

                await self.session.commit()
                logger.info(
                    f"[OrderProjection] Successfully shipped OrderReadModel: {event.order_id}"
                )
            else:
                logger.warning(
                    f"[OrderProjection] OrderReadModel not found for order_id: {event.order_id}"
                )
        except Exception as e:
            logger.error(
                f"[OrderProjection] Error shipping OrderReadModel for order {event.order_id}: {str(e)}",
                exc_info=True,
            )
            await self.session.rollback()
            raise
