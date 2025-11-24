"""MockNotificationAdapter - Mock 通知适配器

用于开发和测试环境的模拟通知实现。
符合六边形架构：实现 INotificationService Port。

特点：
- 自动生成通知ID
- 所有通知操作立即成功
- 记录通知历史（内存）
- 控制台输出通知内容（便于调试）
"""

from __future__ import annotations

import uuid
from datetime import datetime

from contexts.ordering.domain.ports.services.i_notification_service import (
    INotificationService,
    NotificationPriority,
    NotificationRequest,
    NotificationResult,
    NotificationType,
)


class MockNotificationAdapter(INotificationService):
    """Mock 通知适配器（用于测试和开发）

    实现：INotificationService (domain/ports/services/i_notification_service.py)

    特性：
    - 所有通知操作自动成功
    - 生成模拟通知ID
    - 内存记录通知历史
    - 控制台输出通知内容
    """

    def __init__(self, verbose: bool = True):
        """初始化 Mock 通知适配器

        Args:
            verbose: 是否输出详细日志
        """
        self._notifications: list[NotificationResult] = []  # 通知历史
        self._verbose = verbose

    async def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """发送通知（Mock 实现 - 自动成功）

        Args:
            request: 通知请求

        Returns:
            NotificationResult: 通知成功结果
        """
        # 生成通知ID
        notification_id = f"NOTIF_{uuid.uuid4().hex[:12].upper()}"

        # 创建通知结果
        result = NotificationResult(
            notification_id=notification_id,
            success=True,
            message="Notification sent successfully",
            sent_at=datetime.now().isoformat(),
        )

        # 记录通知
        self._notifications.append(result)

        # 输出通知内容（便于调试）
        if self._verbose:
            self._print_notification(request, result)

        return result

    async def send_order_created(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单创建通知

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        request = NotificationRequest(
            recipient=customer_email,
            subject="订单创建成功",
            content=f"您的订单 {order_id} 已创建成功！我们将尽快为您处理。",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
        )

        return await self.send_notification(request)

    async def send_order_paid(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单支付成功通知

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        request = NotificationRequest(
            recipient=customer_email,
            subject="支付成功",
            content=f"您的订单 {order_id} 已支付成功！我们将尽快为您发货。",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    async def send_order_shipped(
        self, order_id: str, customer_email: str, tracking_number: str
    ) -> NotificationResult:
        """发送订单发货通知

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱
            tracking_number: 物流单号

        Returns:
            NotificationResult: 通知结果
        """
        request = NotificationRequest(
            recipient=customer_email,
            subject="订单已发货",
            content=f"您的订单 {order_id} 已发货！\n物流单号：{tracking_number}\n预计2-3个工作日送达。",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    async def send_order_delivered(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单送达通知

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        request = NotificationRequest(
            recipient=customer_email,
            subject="订单已送达",
            content=f"您的订单 {order_id} 已送达！感谢您的购买，期待您的好评！",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
        )

        return await self.send_notification(request)

    async def send_order_cancelled(
        self, order_id: str, customer_email: str, reason: str
    ) -> NotificationResult:
        """发送订单取消通知

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱
            reason: 取消原因

        Returns:
            NotificationResult: 通知结果
        """
        request = NotificationRequest(
            recipient=customer_email,
            subject="订单已取消",
            content=f"您的订单 {order_id} 已取消。\n取消原因：{reason}\n如有疑问，请联系客服。",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    # ============ 辅助方法 ============

    def _print_notification(self, request: NotificationRequest, result: NotificationResult):
        """打印通知内容（便于调试）"""
        print("\n" + "=" * 70)
        print(f"📧 [MockNotification] {result.notification_id}")
        print("=" * 70)
        print(f"收件人: {request.recipient}")
        print(f"类型: {request.notification_type.value}")
        print(f"优先级: {request.priority.value}")
        print(f"主题: {request.subject}")
        print(f"内容:\n{request.content}")
        print(f"发送时间: {result.sent_at}")
        print("=" * 70 + "\n")

    def get_notification_history(self) -> list[NotificationResult]:
        """获取通知历史（仅用于测试）"""
        return self._notifications.copy()

    def get_notification_count(self) -> int:
        """获取通知数量（仅用于测试）"""
        return len(self._notifications)

    def clear_history(self):
        """清空通知历史（仅用于测试）"""
        self._notifications.clear()
        print("🧹 [MockNotification] Notification history cleared")
