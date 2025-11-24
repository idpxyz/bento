"""INotificationService - Secondary Port（被驱动端口）

通知服务接口，定义 Ordering Context 发送通知的契约。
符合六边形架构原则：Domain 层定义接口，Infrastructure 层实现。

Port vs Adapter:
- Port（本文件）: Domain 层定义的接口契约
- Adapter（infrastructure/adapters/）: 接口的具体技术实现
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class NotificationType(str, Enum):
    """通知类型枚举"""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WECHAT = "wechat"


class NotificationPriority(str, Enum):
    """通知优先级枚举"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class NotificationRequest:
    """通知请求（值对象）"""

    recipient: str  # 接收者（邮箱、手机号等）
    subject: str  # 主题/标题
    content: str  # 内容
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    template_id: str | None = None  # 模板ID（如使用模板）
    template_data: dict | None = None  # 模板数据


@dataclass(frozen=True)
class NotificationResult:
    """通知结果（值对象）"""

    notification_id: str  # 通知ID
    success: bool
    message: str = ""
    sent_at: str | None = None


class INotificationService(ABC):
    """通知服务接口（Secondary Port - 被驱动端口）

    职责：
    1. 定义 Ordering BC 发送通知的契约
    2. 隔离通知渠道的变化（反腐败层）
    3. 支持依赖倒置（Domain 不依赖具体通知实现）

    实现方式由 Adapter 决定：
    - EmailAdapter: 邮件通知（SMTP、SendGrid 等）
    - SmsAdapter: 短信通知（阿里云、腾讯云等）
    - PushAdapter: 推送通知（APNs、FCM 等）
    - MockNotificationAdapter: 模拟通知（测试）
    """

    @abstractmethod
    async def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """发送通知

        Args:
            request: 通知请求

        Returns:
            NotificationResult: 通知结果
        """
        pass

    @abstractmethod
    async def send_order_created(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单创建通知（业务方法）

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        pass

    @abstractmethod
    async def send_order_paid(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单支付成功通知（业务方法）

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        pass

    @abstractmethod
    async def send_order_shipped(
        self, order_id: str, customer_email: str, tracking_number: str
    ) -> NotificationResult:
        """发送订单发货通知（业务方法）

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱
            tracking_number: 物流单号

        Returns:
            NotificationResult: 通知结果
        """
        pass

    @abstractmethod
    async def send_order_delivered(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单送达通知（业务方法）

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱

        Returns:
            NotificationResult: 通知结果
        """
        pass

    @abstractmethod
    async def send_order_cancelled(
        self, order_id: str, customer_email: str, reason: str
    ) -> NotificationResult:
        """发送订单取消通知（业务方法）

        Args:
            order_id: 订单ID
            customer_email: 客户邮箱
            reason: 取消原因

        Returns:
            NotificationResult: 通知结果
        """
        pass
