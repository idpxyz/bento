"""Order Read Service - P3 高级特性：使用读模型的高性能查询服务"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.infrastructure.models.read_models.order_read_model import (
    OrderReadModel,
)


@dataclass
class OrderSummary:
    """订单摘要（读模型）"""
    
    id: str
    customer_id: str
    status: str
    total_amount: float
    items_count: int
    created_at: str
    paid_at: str | None = None
    shipped_at: str | None = None


class OrderReadService:
    """使用读模型的查询服务
    
    P3 高级特性：CQRS 读服务
    
    优势：
    - 数据库级过滤（高性能）
    - 无需 JOIN
    - 可以按计算字段排序/过滤
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_orders(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[OrderSummary]:
        """搜索订单（高性能）
        
        使用读模型，支持：
        - 按客户过滤
        - 按状态过滤
        - 按金额范围过滤 ✨ 数据库级过滤
        - 排序、分页
        
        Args:
            customer_id: 客户ID（可选）
            status: 订单状态（可选）
            min_amount: 最小金额（可选）
            max_amount: 最大金额（可选）
            limit: 返回数量
            offset: 偏移量
            
        Returns:
            订单摘要列表
        """
        stmt = select(OrderReadModel)
        
        # ✅ 数据库级过滤 - 高性能！
        if customer_id:
            stmt = stmt.where(OrderReadModel.customer_id == customer_id)
        
        if status:
            stmt = stmt.where(OrderReadModel.status == status)
        
        if min_amount is not None:
            stmt = stmt.where(OrderReadModel.total_amount >= min_amount)
        
        if max_amount is not None:
            stmt = stmt.where(OrderReadModel.total_amount <= max_amount)
        
        # ✅ 可以使用索引排序
        stmt = stmt.order_by(OrderReadModel.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [
            OrderSummary(
                id=m.id,
                customer_id=m.customer_id,
                status=m.status,
                total_amount=m.total_amount,
                items_count=m.items_count,
                created_at=m.created_at.isoformat() if m.created_at else "",
                paid_at=m.paid_at.isoformat() if m.paid_at else None,
                shipped_at=m.shipped_at.isoformat() if m.shipped_at else None,
            )
            for m in models
        ]
    
    async def get_order_summary(self, order_id: str) -> OrderSummary | None:
        """获取订单摘要
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单摘要或 None
        """
        result = await self.session.execute(
            select(OrderReadModel).where(OrderReadModel.id == order_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return OrderSummary(
            id=model.id,
            customer_id=model.customer_id,
            status=model.status,
            total_amount=model.total_amount,
            items_count=model.items_count,
            created_at=model.created_at.isoformat() if model.created_at else "",
            paid_at=model.paid_at.isoformat() if model.paid_at else None,
            shipped_at=model.shipped_at.isoformat() if model.shipped_at else None,
        )
