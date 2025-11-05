"""
Sentry集成模块
用于错误监控和性能追踪
"""
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

import sentry_sdk
from sentry_sdk import capture_exception, capture_message, set_context, set_tag
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.tracing import Span as SentrySpan
from sentry_sdk.tracing import Transaction

from ..core import SpanKind, TracingConfig
from .tracer import BaseSpan, BaseTracer

logger = logging.getLogger(__name__)

class SentrySpan(BaseSpan):
    """Sentry Span实现"""
    
    def __init__(
        self, 
        name: str, 
        sentry_span: Optional[SentrySpan] = None,
        trace_id: Optional[str] = None, 
        parent_span_id: Optional[str] = None
    ):
        """初始化SentrySpan
        
        Args:
            name: Span名称
            sentry_span: Sentry原生Span
            trace_id: 追踪ID
            parent_span_id: 父Span ID
        """
        super().__init__(name, trace_id, parent_span_id)
        self._sentry_span = sentry_span or sentry_sdk.start_span(
            op=name,
            description=name
        )
        
        # 标记span类型(Transaction或Span)，用于适配不同的API
        self._is_transaction = isinstance(self._sentry_span, Transaction)
        
        logger.debug(f"Created SentrySpan: {name}, type: {'Transaction' if self._is_transaction else 'Span'}")
    
    def set_attribute(self, key: str, value: Any) -> None:
        """设置Span属性
        
        Args:
            key: 属性名
            value: 属性值
        """
        super().set_attribute(key, value)
        
        try:
            # 设置Sentry标签和上下文
            if key.startswith("http.") or key in ("error", "error.type", "error.message"):
                # 将重要的属性设置为标签方便搜索
                set_tag(key, str(value))
            else:
                # 为Transaction和Span使用通用的上下文设置方式
                set_context("span_attributes", {key: value})
        except Exception as e:
            logger.error(f"Error setting attribute on span: {e}")
    
    def record_exception(self, exception: Exception) -> None:
        """记录异常
        
        Args:
            exception: 异常对象
        """
        super().record_exception(exception)
        
        try:
            # 向Sentry报告异常
            with sentry_sdk.push_scope() as scope:
                # 添加span信息到scope
                scope.set_tag("trace_id", self.trace_id)
                scope.set_tag("span_id", self.span_id)
                if self.parent_span_id:
                    scope.set_tag("parent_span_id", self.parent_span_id)
                
                # 添加其他属性
                for key, value in self._attributes.items():
                    scope.set_tag(key, str(value))
                
                # 捕获异常
                capture_exception(exception)
        except Exception as e:
            logger.error(f"Error recording exception: {e}")
    
    def _export(self) -> None:
        """导出Span到Sentry"""
        try:
            # 结束Sentry Span
            if hasattr(self._sentry_span, "finish"):
                self._sentry_span.finish()
        except Exception as e:
            logger.error(f"Error exporting span: {e}")


class SentryTracer(BaseTracer):
    """Sentry追踪器实现"""
    
    def __init__(
        self, 
        service_name: str, 
        environment: str = "development",
        dsn: Optional[str] = None,
        sample_rate: float = 1.0,
        traces_sample_rate: float = 0.1,
        max_breadcrumbs: int = 100,
        debug: bool = False,
        enable_tracing: bool = True,
        ignore_errors: Optional[List[str]] = None,
        ignore_paths: Optional[List[str]] = None
    ):
        """初始化Sentry追踪器
        
        Args:
            service_name: 服务名称
            environment: 环境名称
            dsn: Sentry DSN
            sample_rate: 事件采样率
            traces_sample_rate: 追踪采样率
            max_breadcrumbs: 最大面包屑数量
            debug: 是否启用调试模式
            enable_tracing: 是否启用追踪
            ignore_errors: 忽略的错误类型列表
            ignore_paths: 忽略的路径列表
        """
        super().__init__(service_name, sample_rate)
        
        # 默认忽略的路径
        default_ignore_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        if ignore_paths:
            default_ignore_paths.extend(ignore_paths)
        
        # 初始化Sentry SDK
        if dsn:
            try:
                sentry_sdk.init(
                    dsn=dsn,
                    environment=environment,
                    release=None,  # 可以添加版本信息
                    sample_rate=sample_rate,
                    traces_sample_rate=traces_sample_rate,
                    max_breadcrumbs=max_breadcrumbs,
                    debug=debug,
                    enable_tracing=enable_tracing,
                    integrations=[
                        FastApiIntegration(transaction_style="url"),
                        SqlalchemyIntegration(),
                        RedisIntegration(),
                    ],
                    ignore_errors=ignore_errors or [],
                    # 忽略特定路径的错误
                    before_send=lambda event, hint: self._before_send(event, hint, default_ignore_paths)
                )
                
                # 设置全局标签
                set_tag("service", service_name)
                set_tag("environment", environment)
                
                logger.info(f"Sentry initialized for service: {service_name}, environment: {environment}")
            except Exception as e:
                logger.error(f"Failed to initialize Sentry: {e}")
        else:
            logger.warning("Sentry DSN not provided, Sentry integration disabled")
    
    def _before_send(self, event: Dict, hint: Dict, ignore_paths: List[str]) -> Optional[Dict]:
        """事件发送前处理
        
        Args:
            event: Sentry事件
            hint: 事件提示
            ignore_paths: 忽略的路径列表
            
        Returns:
            Optional[Dict]: 处理后的事件，返回None表示丢弃事件
        """
        try:
            # 获取请求URL
            request = event.get("request", {})
            url = request.get("url", "")
            
            # 检查是否是忽略的路径
            for path in ignore_paths:
                if re.search(path, url):
                    return None  # 忽略事件
            
            return event
        except Exception as e:
            logger.error(f"Error in before_send: {e}")
            return event  # 在错误情况下仍然发送事件
    
    async def _create_span(
        self, 
        name: str, 
        kind: SpanKind,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> SentrySpan:
        """创建新的Span
        
        Args:
            name: Span名称
            kind: Span类型
            trace_id: 追踪ID，如果为None则创建新的
            parent_span_id: 父Span ID，如果为None则为根Span
            
        Returns:
            SentrySpan: 创建的Span
        """
        try:
            sentry_span = None
            
            # 为顶级Span创建Transaction，为子Span创建普通Span
            if parent_span_id is None and not sentry_sdk.Hub.current.scope.span:
                # 创建Transaction
                op_name = f"{kind.value}.{name}"
                logger.debug(f"Creating Transaction: {name}, op: {op_name}")
                sentry_transaction = Transaction(
                    op=op_name,
                    name=name,
                    trace_id=trace_id or uuid.uuid4().hex,
                )
                sentry_sdk.Hub.current.start_transaction(sentry_transaction)
                span = SentrySpan(name, sentry_transaction, trace_id, parent_span_id)
            else:
                # 创建子Span
                op_name = f"{kind.value}.{name}"
                logger.debug(f"Creating child Span: {name}, op: {op_name}")
                with sentry_sdk.Hub.current.start_span(
                    op=op_name,
                    description=name
                ) as sentry_span:
                    span = SentrySpan(name, sentry_span, trace_id, parent_span_id)
            
            # 设置基本标签 - 使用安全的方式设置
            try:
                span.set_attribute("span.kind", kind.value)
            except Exception as e:
                logger.error(f"Error setting span.kind attribute: {e}")
            
            return span
        except Exception as e:
            logger.error(f"Error creating span: {e}")
            # 创建一个没有底层Sentry span的span，避免应用崩溃
            return SentrySpan(name, None, trace_id, parent_span_id)
    
    async def _end_span(self, span: SentrySpan) -> None:
        """结束并导出Span
        
        Args:
            span: 要结束的Span
        """
        span.end()
        span._export()


def before_send_handler(event: Dict, hint: Dict, ignore_paths: List[str]) -> Optional[Dict]:
    """事件发送前处理
    
    Args:
        event: Sentry事件
        hint: 事件提示
        ignore_paths: 忽略的路径列表
        
    Returns:
        Optional[Dict]: 处理后的事件，返回None表示丢弃事件
    """
    try:
        # 获取请求URL
        request = event.get("request", {})
        url = request.get("url", "")
        
        # 检查是否是忽略的路径
        for path in ignore_paths:
            if re.search(path, url):
                return None  # 忽略事件
        
        return event
    except Exception as e:
        logger.error(f"Error in before_send: {e}")
        return event  # 在错误情况下仍然发送事件


def configure_sentry(config: TracingConfig, environment: str) -> Optional[SentryTracer]:
    """配置Sentry并返回Sentry追踪器
    
    Args:
        config: 追踪配置
        environment: 环境名称
        
    Returns:
        Optional[SentryTracer]: Sentry追踪器实例，配置失败则返回None
    """
    if not config.enabled:
        logger.info("Tracing disabled, not initializing Sentry")
        return None
    
    if not config.sentry.enabled:
        logger.info("Sentry integration disabled, not initializing Sentry")
        return None
    
    if not config.sentry.dsn:
        logger.info("Sentry DSN not provided, not initializing Sentry")
        return None
    
    # 定义智能采样函数
    def traces_sampler(sampling_context):
        # 获取交易数据
        transaction_context = sampling_context.get("transaction_context", {})
        
        # 根据交易名称和操作类型采样
        transaction_name = transaction_context.get("name", "")
        op = transaction_context.get("op", "")
        
        # 始终捕获关键API (例如 /api/critical)
        if "critical" in transaction_name.lower():
            return 1.0
            
        # 高度关注性能监控的操作类型
        high_value_ops = ["http.server", "db.query", "http.client"]
        if op in high_value_ops:
            return 0.5  # 50% 采样率
            
        # 对于潜在错误路径增加采样率
        if "error" in transaction_name.lower() or "exception" in transaction_name.lower():
            return 0.8  # 80% 采样率
            
        # 对于健康检查和指标端点降低采样率
        if any(path in transaction_name.lower() for path in ["/health", "/metrics", "/ping"]):
            return 0.01  # 1% 采样率
            
        # 对于开发环境提高采样率
        if environment in ["dev", "development", "test"]:
            return min(config.sentry.traces_sample_rate * 2.0, 1.0)  # 加倍采样率，但不超过1.0
        
        # 默认使用配置的采样率
        return config.sentry.traces_sample_rate
    
    try:
        service_name = config.service_name if hasattr(config, 'service_name') else 'unknown-service'
        logger.info(f"Configuring Sentry with DSN for service: {service_name}, env: {environment}")
        logger.info(f"Using intelligent sampling with traces_sampler function")
        
        # 初始化SDK，使用智能采样
        sentry_sdk.init(
            dsn=config.sentry.dsn,
            environment=environment,
            release=None,  # 可以添加版本信息
            traces_sampler=traces_sampler,  # 使用智能采样代替固定比率
            max_breadcrumbs=config.sentry.max_breadcrumbs,
            debug=config.sentry.debug,
            send_default_pii=config.sentry.send_default_pii,
            integrations=[
                FastApiIntegration(transaction_style="url"),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            # 忽略特定路径的错误 - 创建一个匿名函数传递参数
            before_send=lambda event, hint: before_send_handler(event, hint, config.ignored_paths)
        )
        
        # 创建Sentry追踪器
        tracer = SentryTracer(
            service_name=service_name,
            environment=environment,
            dsn=config.sentry.dsn,
            sample_rate=config.sample_rate,
            traces_sample_rate=config.sentry.traces_sample_rate,  # 这个值实际上被traces_sampler覆盖
            max_breadcrumbs=config.sentry.max_breadcrumbs,
            debug=config.sentry.debug,
            enable_tracing=True,
            ignore_paths=config.ignored_paths
        )
        
        return tracer
    except Exception as e:
        logger.error(f"Failed to configure Sentry: {e}")
        return None 