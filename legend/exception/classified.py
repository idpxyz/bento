"""分类异常模块

提供各种分类的异常实现，如领域异常、应用异常等
"""

from typing import Dict, Optional

from idp.framework.exception.base import IDPBaseException
from idp.framework.exception.metadata import ExceptionCategory


class InterfaceException(IDPBaseException):
    """接口异常：表示与外部接口交互时发生的错误"""
    def __init__(self, **kwargs):
        if "category"  in kwargs:
            raise ValueError("category 不能在接口异常中指定, 它由分类异常自动设置")
        kwargs["category"] = ExceptionCategory.INTERFACE
        super().__init__(**kwargs)


class DomainException(IDPBaseException):
    """领域异常：表示业务领域中的规则违反或不符合领域逻辑的情况"""
    def __init__(self, **kwargs):
        if "category"  in kwargs:
            raise ValueError("category 不能在领域异常中指定, 它由分类异常自动设置")
        kwargs["category"] = ExceptionCategory.DOMAIN
        super().__init__(**kwargs)


class ApplicationException(IDPBaseException):
    """应用异常：表示应用层的错误，如用例执行失败等"""
    def __init__(self, **kwargs):
        if "category"  in kwargs:
            raise ValueError("category 不能在应用异常中指定, 它由分类异常自动设置")
        kwargs["category"] = ExceptionCategory.APPLICATION
        super().__init__(**kwargs)


class InfrastructureException(IDPBaseException):
    """基础设施异常：表示基础设施层的错误，如数据库连接失败等"""
    def __init__(self, **kwargs):
        if "category"  in kwargs:
            raise ValueError("category 不能在基础设施异常中指定, 它由分类异常自动设置")
        kwargs["category"] = ExceptionCategory.INFRASTRUCTURE
        super().__init__(**kwargs)
