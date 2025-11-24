"""Order event handler - P3 高级特性：事件驱动架构"""

import logging

from bento.domain.domain_event import DomainEvent

from contexts.ordering.domain.events.ordercancelled_event import OrderCancelledEvent
from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent
from contexts.ordering.domain.events.orderdelivered_event import OrderDeliveredEvent
from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent
from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent

logger = logging.getLogger(__name__)


class OrderEventHandler:
    """处理订单领域事件

    P3 高级特性：
    - 事件驱动架构
    - 关注点分离
    - 与外部系统集成点

    最佳实践：
    - 处理器应该是幂等的（可以安全地多次调用）
    - 每个处理器做好一件事
    - 失败被记录但不阻止事件处理
    """

    def __init__(self) -> None:
        """初始化事件处理器"""
        self._handlers = {
            "order_created": self._handle_order_created,
            "order_paid": self._handle_order_paid,
            "order_shipped": self._handle_order_shipped,
            "order_delivered": self._handle_order_delivered,
            "order_cancelled": self._handle_order_cancelled,
        }

    async def handle(self, event: DomainEvent) -> None:
        """路由事件到特定处理器

        Args:
            event: 领域事件
        """
        event_name = event.name or event.__class__.__name__
        handler = self._handlers.get(event_name)

        if handler:
            try:
                await handler(event)
            except Exception as e:
                # 记录但不抛出 - 事件应该是幂等的
                logger.error(
                    f"Error handling {event_name}: {e}",
                    exc_info=True,
                    extra={
                        "event_id": str(event.event_id),
                        "event_name": event_name,
                    },
                )
        else:
            logger.debug(f"No handler found for event: {event_name}")

    async def _handle_order_created(self, event: OrderCreatedEvent) -> None:
        """处理订单创建事件

        触发多个副作用：
        - 发送确认邮件
        - 预留库存
        - 通知仓库
        - 创建分析记录

        Args:
            event: OrderCreated 事件
        """
        logger.info(
            f"📦 Order created: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": event.order_id,
                "customer_id": event.customer_id,
                "total": event.total,
                "item_count": event.item_count,
            },
        )

        # 发送订单确认邮件
        await self._send_order_confirmation_email(event)

        # 预留库存
        await self._reserve_inventory(event)

        # 通知仓库
        await self._notify_warehouse(event)

        logger.info(f"✅ Finished processing OrderCreated for order {event.order_id}")

    async def _handle_order_paid(self, event: OrderPaidEvent) -> None:
        """处理订单支付事件

        支付触发履约工作流：
        - 发送支付收据
        - 启动履约流程
        - 更新分析数据

        Args:
            event: OrderPaid 事件
        """
        logger.info(
            f"💳 Order paid: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": event.order_id,
                "customer_id": event.customer_id,
                "total": event.total,
            },
        )

        # 发送支付收据
        await self._send_payment_receipt(event)

        # 启动履约流程
        await self._initiate_fulfillment(event)

        # 更新分析数据
        await self._update_payment_analytics(event)

        logger.info(f"✅ Finished processing OrderPaid for order {event.order_id}")

    async def _handle_order_shipped(self, event: OrderShippedEvent) -> None:
        """处理订单发货事件

        Args:
            event: OrderShipped 事件
        """
        logger.info(
            f"🚚 Order shipped: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": event.order_id,
                "tracking_number": event.tracking_number,
            },
        )

        # 发送发货通知
        await self._send_shipping_notification(event)

        logger.info(f"✅ Finished processing OrderShipped for order {event.order_id}")

    async def _handle_order_delivered(self, event: OrderDeliveredEvent) -> None:
        """处理订单送达事件

        Args:
            event: OrderDelivered 事件
        """
        logger.info(
            f"✅ Order delivered: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": event.order_id,
            },
        )

        # 发送送达确认
        await self._send_delivery_confirmation(event)

        logger.info(f"✅ Finished processing OrderDelivered for order {event.order_id}")

    async def _handle_order_cancelled(self, event: OrderCancelledEvent) -> None:
        """处理订单取消事件

        取消触发清理工作流：
        - 发送取消邮件
        - 释放库存
        - 处理退款（如果已支付）

        Args:
            event: OrderCancelled 事件
        """
        logger.info(
            f"❌ Order cancelled: {event.order_id}",
            extra={
                "event_id": str(event.event_id),
                "order_id": event.order_id,
                "reason": event.reason,
            },
        )

        # 发送取消邮件
        await self._send_cancellation_email(event)

        # 释放库存
        await self._release_inventory(event)

        # 处理退款（如果需要）
        await self._process_refund_if_needed(event)

        logger.info(f"✅ Finished processing OrderCancelled for order {event.order_id}")

    # ==================== 模拟集成方法 ====================
    # 在生产环境中，这些方法会调用真实的服务

    async def _send_order_confirmation_email(self, event: OrderCreatedEvent) -> None:
        """发送订单确认邮件（模拟）"""
        logger.info(f"📧 Sending order confirmation email to customer {event.customer_id}")
        # TODO: 集成邮件服务 (SendGrid, AWS SES, etc.)

    async def _reserve_inventory(self, event: OrderCreatedEvent) -> None:
        """预留库存（模拟）"""
        logger.info(f"📦 Reserving inventory for order {event.order_id} ({event.item_count} items)")
        # TODO: 集成库存服务

    async def _notify_warehouse(self, event: OrderCreatedEvent) -> None:
        """通知仓库（模拟）"""
        logger.info(f"🏭 Notifying warehouse of order {event.order_id}")
        # TODO: 集成仓库管理系统

    async def _send_payment_receipt(self, event: OrderPaidEvent) -> None:
        """发送支付收据（模拟）"""
        logger.info(f"💳 Sending payment receipt for order {event.order_id} (${event.total})")
        # TODO: 集成邮件服务

    async def _initiate_fulfillment(self, event: OrderPaidEvent) -> None:
        """启动履约流程（模拟）"""
        logger.info(f"📤 Initiating fulfillment for order {event.order_id}")
        # TODO: 集成履约服务

    async def _update_payment_analytics(self, event: OrderPaidEvent) -> None:
        """更新支付分析数据（模拟）"""
        logger.info(f"📊 Updating analytics for payment: {event.order_id} (${event.total})")
        # TODO: 集成分析平台

    async def _send_shipping_notification(self, event: OrderShippedEvent) -> None:
        """发送发货通知（模拟）"""
        logger.info(f"📧 Sending shipping notification for order {event.order_id}")
        # TODO: 集成邮件服务

    async def _send_delivery_confirmation(self, event: OrderDeliveredEvent) -> None:
        """发送送达确认（模拟）"""
        logger.info(f"📧 Sending delivery confirmation for order {event.order_id}")
        # TODO: 集成邮件服务

    async def _send_cancellation_email(self, event: OrderCancelledEvent) -> None:
        """发送取消邮件（模拟）"""
        logger.info(
            f"📧 Sending cancellation email for order {event.order_id}. Reason: {event.reason}"
        )
        # TODO: 集成邮件服务

    async def _release_inventory(self, event: OrderCancelledEvent) -> None:
        """释放预留库存（模拟）"""
        logger.info(f"📦 Releasing inventory for order {event.order_id}")
        # TODO: 集成库存服务

    async def _process_refund_if_needed(self, event: OrderCancelledEvent) -> None:
        """处理退款（如果已支付）（模拟）"""
        logger.info(f"💰 Processing refund check for order {event.order_id} (if applicable)")
        # TODO: 集成支付服务
