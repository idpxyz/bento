"""Route Plan 状态值对象

定义路线计划可能的状态。
"""
from enum import Enum


class RoutePlanStatus(str, Enum):
    """路线计划状态枚举"""

    # 初始状态
    DRAFT = "DRAFT"                    # 草稿
    PENDING_REVIEW = "PENDING_REVIEW"  # 待审核
    REJECTED = "REJECTED"              # 已拒绝

    # 规划状态
    APPROVED = "APPROVED"              # 已审核通过
    PLANNING = "PLANNING"              # 规划中
    PLANNED = "PLANNED"                # 已规划完成

    # 执行状态
    READY = "READY"                    # 就绪（可执行）
    IN_PROGRESS = "IN_PROGRESS"        # 执行中
    PAUSED = "PAUSED"                  # 已暂停

    # 完成状态
    COMPLETED = "COMPLETED"            # 已完成
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"  # 部分完成
    FAILED = "FAILED"                  # 执行失败
    CANCELLED = "CANCELLED"            # 已取消
    ARCHIVED = "ARCHIVED"              # 已归档

    # 重试状态
    RETRY_PLANNING = "RETRY_PLANNING"  # 重试规划中
    RETRY_READY = "RETRY_READY"        # 重试就绪
