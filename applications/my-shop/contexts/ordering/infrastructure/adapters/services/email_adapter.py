"""EmailAdapter - SMTP 邮件通知适配器

使用 SMTP 协议发送邮件通知。
符合六边形架构：实现 INotificationService Port。

支持：
- SMTP/SMTP_SSL
- 邮件模板
- HTML/文本格式
- 异步发送
"""

from __future__ import annotations

import asyncio
import smtplib
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from contexts.ordering.domain.ports.services.i_notification_service import (
    INotificationService,
    NotificationPriority,
    NotificationRequest,
    NotificationResult,
    NotificationType,
)


@dataclass
class EmailConfig:
    """邮件配置"""

    smtp_host: str  # SMTP 服务器地址
    smtp_port: int  # SMTP 端口
    smtp_user: str  # SMTP 用户名
    smtp_password: str  # SMTP 密码
    from_email: str  # 发件人邮箱
    from_name: str = "My Shop"  # 发件人名称
    use_ssl: bool = True  # 是否使用 SSL
    use_tls: bool = False  # 是否使用 TLS


class EmailAdapter(INotificationService):
    """SMTP 邮件通知适配器

    实现：INotificationService (domain/ports/services/i_notification_service.py)

    特性：
    - 使用 SMTP 协议发送邮件
    - 支持 HTML 和文本格式
    - 异步发送（不阻塞业务流程）
    - 支持邮件模板

    配置示例：
    ```python
    config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="your-email@gmail.com",
        smtp_password="your-app-password",
        from_email="noreply@myshop.com",
        from_name="My Shop",
        use_ssl=True,
    )
    adapter = EmailAdapter(config)
    ```
    """

    def __init__(self, config: EmailConfig):
        """初始化邮件适配器

        Args:
            config: 邮件配置
        """
        self.config = config

    async def send_notification(self, request: NotificationRequest) -> NotificationResult:
        """发送通知（仅支持邮件）

        Args:
            request: 通知请求

        Returns:
            NotificationResult: 通知结果
        """
        if request.notification_type != NotificationType.EMAIL:
            return NotificationResult(
                notification_id=f"EMAIL_{uuid.uuid4().hex[:12].upper()}",
                success=False,
                message=f"Unsupported notification type: {request.notification_type}",
            )

        try:
            # 在线程池中发送邮件（避免阻塞）
            await asyncio.to_thread(
                self._send_email,
                to_email=request.recipient,
                subject=request.subject,
                content=request.content,
                is_html=True,
            )

            notification_id = f"EMAIL_{uuid.uuid4().hex[:12].upper()}"

            print(f"📧 [EmailAdapter] Email sent to {request.recipient}: {request.subject}")

            return NotificationResult(
                notification_id=notification_id,
                success=True,
                message="Email sent successfully",
                sent_at=datetime.now().isoformat(),
            )

        except Exception as e:
            print(f"❌ [EmailAdapter] Failed to send email to {request.recipient}: {str(e)}")

            return NotificationResult(
                notification_id=f"EMAIL_{uuid.uuid4().hex[:12].upper()}",
                success=False,
                message=f"Failed to send email: {str(e)}",
            )

    async def send_order_created(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单创建通知"""
        subject = "订单创建成功 - My Shop"
        content = self._render_order_created_template(order_id)

        request = NotificationRequest(
            recipient=customer_email,
            subject=subject,
            content=content,
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
        )

        return await self.send_notification(request)

    async def send_order_paid(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单支付成功通知"""
        subject = "支付成功 - My Shop"
        content = self._render_order_paid_template(order_id)

        request = NotificationRequest(
            recipient=customer_email,
            subject=subject,
            content=content,
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    async def send_order_shipped(
        self, order_id: str, customer_email: str, tracking_number: str
    ) -> NotificationResult:
        """发送订单发货通知"""
        subject = "订单已发货 - My Shop"
        content = self._render_order_shipped_template(order_id, tracking_number)

        request = NotificationRequest(
            recipient=customer_email,
            subject=subject,
            content=content,
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    async def send_order_delivered(self, order_id: str, customer_email: str) -> NotificationResult:
        """发送订单送达通知"""
        subject = "订单已送达 - My Shop"
        content = self._render_order_delivered_template(order_id)

        request = NotificationRequest(
            recipient=customer_email,
            subject=subject,
            content=content,
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
        )

        return await self.send_notification(request)

    async def send_order_cancelled(
        self, order_id: str, customer_email: str, reason: str
    ) -> NotificationResult:
        """发送订单取消通知"""
        subject = "订单已取消 - My Shop"
        content = self._render_order_cancelled_template(order_id, reason)

        request = NotificationRequest(
            recipient=customer_email,
            subject=subject,
            content=content,
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
        )

        return await self.send_notification(request)

    # ============ 私有方法 ============

    def _send_email(self, to_email: str, subject: str, content: str, is_html: bool = True):
        """发送邮件（同步方法，在线程池中调用）

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            is_html: 是否为 HTML 格式
        """
        # 创建邮件
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # 添加内容
        if is_html:
            msg.attach(MIMEText(content, "html", "utf-8"))
        else:
            msg.attach(MIMEText(content, "plain", "utf-8"))

        # 发送邮件
        if self.config.use_ssl:
            # 使用 SSL
            with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port) as server:
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
        else:
            # 使用 TLS 或不加密
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)

    # ============ 邮件模板 ============

    def _render_order_created_template(self, order_id: str) -> str:
        """渲染订单创建邮件模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">订单创建成功</h2>
            <p>您好！</p>
            <p>您的订单已创建成功，我们将尽快为您处理。</p>
            <p><strong>订单号：</strong>{order_id}</p>
            <p>您可以随时登录我们的网站查看订单详情。</p>
            <br>
            <p>感谢您的购买！</p>
            <p><em>My Shop 团队</em></p>
        </body>
        </html>
        """

    def _render_order_paid_template(self, order_id: str) -> str:
        """渲染订单支付成功邮件模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2196F3;">支付成功</h2>
            <p>您好！</p>
            <p>您的订单已支付成功，我们将尽快为您发货。</p>
            <p><strong>订单号：</strong>{order_id}</p>
            <p>您可以在订单详情页面查看物流信息。</p>
            <br>
            <p>感谢您的信任！</p>
            <p><em>My Shop 团队</em></p>
        </body>
        </html>
        """

    def _render_order_shipped_template(self, order_id: str, tracking_number: str) -> str:
        """渲染订单发货邮件模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #FF9800;">订单已发货</h2>
            <p>您好！</p>
            <p>您的订单已发货，预计2-3个工作日送达。</p>
            <p><strong>订单号：</strong>{order_id}</p>
            <p><strong>物流单号：</strong>{tracking_number}</p>
            <p>您可以使用物流单号查询配送进度。</p>
            <br>
            <p>感谢您的耐心等待！</p>
            <p><em>My Shop 团队</em></p>
        </body>
        </html>
        """

    def _render_order_delivered_template(self, order_id: str) -> str:
        """渲染订单送达邮件模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">订单已送达</h2>
            <p>您好！</p>
            <p>您的订单已送达，感谢您的购买！</p>
            <p><strong>订单号：</strong>{order_id}</p>
            <p>如果您对商品满意，欢迎给我们好评。如有任何问题，请随时联系客服。</p>
            <br>
            <p>期待再次为您服务！</p>
            <p><em>My Shop 团队</em></p>
        </body>
        </html>
        """

    def _render_order_cancelled_template(self, order_id: str, reason: str) -> str:
        """渲染订单取消邮件模板"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #F44336;">订单已取消</h2>
            <p>您好！</p>
            <p>您的订单已取消。</p>
            <p><strong>订单号：</strong>{order_id}</p>
            <p><strong>取消原因：</strong>{reason}</p>
            <p>如有疑问，请联系客服。</p>
            <br>
            <p>期待再次为您服务！</p>
            <p><em>My Shop 团队</em></p>
        </body>
        </html>
        """
