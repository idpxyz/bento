"""MockPaymentAdapter - Mock 支付适配器

用于开发和测试环境的模拟支付实现。
符合六边形架构：实现 IPaymentService Port。

特点：
- 自动生成交易ID
- 所有支付操作立即成功
- 记录支付历史（内存）
- 支持查询、取消、退款
"""

from __future__ import annotations

import uuid
from datetime import datetime

from contexts.ordering.domain.ports.services.i_payment_service import (
    IPaymentService,
    PaymentMethod,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
)


class MockPaymentAdapter(IPaymentService):
    """Mock 支付适配器（用于测试和开发）

    实现：IPaymentService (domain/ports/services/i_payment_service.py)

    特性：
    - 所有支付操作自动成功
    - 生成模拟交易ID
    - 内存记录支付历史
    - 支持完整的支付流程测试
    """

    def __init__(self):
        """初始化 Mock 支付适配器"""
        self._payments: dict[str, PaymentResult] = {}  # 存储支付记录
        self._refunds: dict[str, float] = {}  # 存储退款记录

    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """处理支付（Mock 实现 - 自动成功）

        Args:
            request: 支付请求

        Returns:
            PaymentResult: 支付成功结果
        """
        # 生成模拟交易ID
        transaction_id = f"MOCK_{uuid.uuid4().hex[:16].upper()}"

        # 创建支付结果
        result = PaymentResult(
            transaction_id=transaction_id,
            status=PaymentStatus.SUCCESS,
            amount=request.amount,
            payment_method=request.payment_method,
            message=f"Mock payment successful for order {request.order_id}",
            paid_at=datetime.now().isoformat(),
        )

        # 记录支付
        self._payments[transaction_id] = result

        print(f"💳 [MockPayment] Payment processed: {transaction_id} - ${request.amount:.2f}")

        return result

    async def query_payment(self, transaction_id: str) -> PaymentResult:
        """查询支付状态

        Args:
            transaction_id: 交易ID

        Returns:
            PaymentResult: 支付结果

        Raises:
            KeyError: 交易不存在
        """
        if transaction_id not in self._payments:
            # 如果交易不存在，返回失败状态
            return PaymentResult(
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                amount=0.0,
                payment_method=PaymentMethod.CREDIT_CARD,
                message="Transaction not found",
            )

        result = self._payments[transaction_id]
        print(f"🔍 [MockPayment] Query payment: {transaction_id} - Status: {result.status}")

        return result

    async def cancel_payment(self, transaction_id: str) -> bool:
        """取消支付

        Args:
            transaction_id: 交易ID

        Returns:
            bool: 是否成功取消
        """
        if transaction_id not in self._payments:
            print(f"⚠️ [MockPayment] Cancel failed: Transaction {transaction_id} not found")
            return False

        # 更新支付状态为已取消
        original = self._payments[transaction_id]
        self._payments[transaction_id] = PaymentResult(
            transaction_id=original.transaction_id,
            status=PaymentStatus.CANCELLED,
            amount=original.amount,
            payment_method=original.payment_method,
            message="Payment cancelled",
            paid_at=original.paid_at,
        )

        print(f"❌ [MockPayment] Payment cancelled: {transaction_id}")

        return True

    async def refund_payment(
        self, transaction_id: str, amount: float | None = None
    ) -> PaymentResult:
        """退款

        Args:
            transaction_id: 交易ID
            amount: 退款金额（None 表示全额退款）

        Returns:
            PaymentResult: 退款结果
        """
        if transaction_id not in self._payments:
            return PaymentResult(
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                amount=0.0,
                payment_method=PaymentMethod.CREDIT_CARD,
                message="Transaction not found for refund",
            )

        original = self._payments[transaction_id]

        # 确定退款金额
        refund_amount = amount if amount is not None else original.amount

        # 检查退款金额是否超过原支付金额
        if refund_amount > original.amount:
            error_msg = (
                f"Refund amount ${refund_amount:.2f} exceeds payment amount ${original.amount:.2f}"
            )
            return PaymentResult(
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                amount=refund_amount,
                payment_method=original.payment_method,
                message=error_msg,
            )

        # 记录退款
        self._refunds[transaction_id] = refund_amount

        # 创建退款结果
        refund_result = PaymentResult(
            transaction_id=f"REFUND_{transaction_id}",
            status=PaymentStatus.REFUNDED,
            amount=refund_amount,
            payment_method=original.payment_method,
            message=f"Refund successful: ${refund_amount:.2f}",
            paid_at=datetime.now().isoformat(),
        )

        print(f"💰 [MockPayment] Refund processed: {transaction_id} - ${refund_amount:.2f}")

        return refund_result

    # ============ 辅助方法 ============

    def get_payment_history(self) -> dict[str, PaymentResult]:
        """获取支付历史（仅用于测试）"""
        return self._payments.copy()

    def clear_history(self):
        """清空支付历史（仅用于测试）"""
        self._payments.clear()
        self._refunds.clear()
        print("🧹 [MockPayment] Payment history cleared")
