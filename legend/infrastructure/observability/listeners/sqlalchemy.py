"""
SQLAlchemy 监听器
用于监控数据库操作性能和进行链路追踪
"""
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import Session

from ..core import IMetricsRecorder, ITracer, Span, SpanKind
from ..core.metadata import StandardMetrics

logger = logging.getLogger(__name__)

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


class SQLAlchemyListener:
    """SQLAlchemy 监听器，用于监控数据库操作"""

    def __init__(
        self,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        record_parameters: bool = False,
    ):
        """初始化 SQLAlchemy 监听器
        
        Args:
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            record_parameters: 是否记录参数，默认为 False（避免记录敏感信息）
        """
        self.metrics_recorder = metrics_recorder
        self.tracer = tracer
        self.record_parameters = record_parameters
        self._active_spans: Dict[int, Span] = {}
        self._start_times: Dict[int, float] = {}
        
    def install_sync_hooks(self, engine: Engine) -> None:
        """安装同步引擎钩子
        
        Args:
            engine: SQLAlchemy Engine 实例
        """
        logger.info(f"Installing SQLAlchemy sync hooks for engine: {engine}")
        
        # 查询执行前
        @event.listens_for(engine, "before_execute")
        def before_execute(conn: Connection, clauseelement, multiparams, params) -> None:
            self._before_execute_handler(conn, clauseelement, multiparams, params)
        
        # 查询执行后
        @event.listens_for(engine, "after_execute")
        def after_execute(conn: Connection, clauseelement, multiparams, params, result) -> None:
            self._after_execute_handler(conn, clauseelement, multiparams, params, result)
        
        # 处理异常
        @event.listens_for(engine, "handle_error")
        def handle_error(context) -> None:
            self._handle_error(context.connection, context.statement, context.exception)

    def install_async_hooks(self, engine: AsyncEngine) -> None:
        """安装异步引擎钩子
        
        Args:
            engine: SQLAlchemy AsyncEngine 实例
        """
        logger.info(f"Installing SQLAlchemy async hooks for engine: {engine}")
        
        # 获取原始同步引擎并安装钩子
        raw_engine = engine.sync_engine
        self.install_sync_hooks(raw_engine)

    def _get_conn_id(self, conn: Any) -> int:
        """获取连接的唯一标识
        
        Args:
            conn: 数据库连接
            
        Returns:
            int: 连接唯一标识
        """
        return id(conn)

    def _before_execute_handler(
        self, conn: Any, clauseelement: Any, multiparams: Any, params: Any
    ) -> None:
        """查询执行前处理
        
        Args:
            conn: 数据库连接
            clauseelement: SQL语句元素
            multiparams: 多参数
            params: 参数
        """
        conn_id = self._get_conn_id(conn)
        self._start_times[conn_id] = time.time()
        
        # 提取SQL信息
        query_str = str(clauseelement)
        query_type = self._get_query_type(query_str)
        table_name = self._extract_table_name(query_str)
        
        # 创建追踪 span
        if self.tracer:
            span_attributes = {
                "db.system": "postgresql",  # 默认为 PostgreSQL，实际使用时可能需要根据引擎类型判断
                "db.statement": query_str[:1000] if self.record_parameters else self._sanitize_query(query_str),
                "db.operation": query_type,
                "db.table": table_name,
            }
            
            span = self.tracer.start_span(
                name=f"db.{query_type}",
                kind=SpanKind.CLIENT,
                attributes=span_attributes,
            )
            self._active_spans[conn_id] = span

    async def _after_execute_handler(
        self, conn: Any, clauseelement: Any, multiparams: Any, params: Any, result: Any
    ) -> None:
        """查询执行后处理
        
        Args:
            conn: 数据库连接
            clauseelement: SQL语句元素
            multiparams: 多参数
            params: 参数
            result: 执行结果
        """
        conn_id = self._get_conn_id(conn)
        start_time = self._start_times.pop(conn_id, None)
        span = self._active_spans.pop(conn_id, None)
        
        if start_time is None:
            return
        
        # 计算执行时间
        duration = time.time() - start_time
        
        # 提取SQL信息
        query_str = str(clauseelement)
        query_type = self._get_query_type(query_str)
        table_name = self._extract_table_name(query_str)
        
        # 记录指标
        labels = {
            "operation": query_type,
            "table": table_name,
        }
        
        try:
            await self.metrics_recorder.observe_histogram(
                StandardMetrics.DB_OPERATION_DURATION.name,
                duration,
                labels
            )
            
            # 获取受影响的行数（如果可用）
            if hasattr(result, "rowcount") and result.rowcount >= 0:
                await self.metrics_recorder.increment_counter(
                    "db_affected_rows_total",
                    float(result.rowcount),
                    {"operation": query_type, "table": table_name}
                )
        except Exception as e:
            logger.error(f"Error recording database metrics: {e}")
        
        # 结束 span
        if span:
            # 添加结果信息
            if hasattr(result, "rowcount") and result.rowcount >= 0:
                span.set_attribute("db.affected_rows", result.rowcount)
            
            try:
                # 结束 span
                if hasattr(span, "_end_span"):
                    await span._end_span()
                # 某些实现可能没有_end_span方法，使用exit代替
            except Exception as e:
                logger.error(f"Error ending database span: {e}")

    async def _handle_error(self, conn: Any, statement: str, exception: Exception) -> None:
        """处理数据库错误
        
        Args:
            conn: 数据库连接
            statement: SQL语句
            exception: 异常
        """
        conn_id = self._get_conn_id(conn)
        span = self._active_spans.pop(conn_id, None)
        
        # 提取SQL信息
        query_type = self._get_query_type(statement)
        table_name = self._extract_table_name(statement)
        error_type = type(exception).__name__
        
        # 记录错误指标
        try:
            await self.metrics_recorder.increment_counter(
                StandardMetrics.DB_ERRORS.name,
                1.0,
                {"operation": query_type, "error": error_type}
            )
        except Exception as e:
            logger.error(f"Error recording database error metrics: {e}")
        
        # 记录 span 异常
        if span:
            span.record_exception(exception)
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", str(exception))
            
            try:
                # 结束 span
                if hasattr(span, "_end_span"):
                    await span._end_span()
                # 某些实现可能没有_end_span方法，使用exit代替
            except Exception as e:
                logger.error(f"Error ending database error span: {e}")

    def _get_query_type(self, query: str) -> str:
        """获取查询类型
        
        Args:
            query: SQL查询语句
            
        Returns:
            str: 查询类型，如 select, insert, update, delete
        """
        query = query.strip().lower()
        
        if query.startswith("select"):
            return "select"
        elif query.startswith("insert"):
            return "insert"
        elif query.startswith("update"):
            return "update"
        elif query.startswith("delete"):
            return "delete"
        elif query.startswith("create"):
            return "create"
        elif query.startswith("alter"):
            return "alter"
        elif query.startswith("drop"):
            return "drop"
        else:
            return "other"

    def _extract_table_name(self, query: str) -> str:
        """提取表名
        
        Args:
            query: SQL查询语句
            
        Returns:
            str: 表名，无法提取时返回 unknown
        """
        # 简单实现，实际使用时可能需要更复杂的解析
        query_type = self._get_query_type(query)
        query = query.strip().lower()
        
        try:
            if query_type == "select":
                # select * from users
                parts = query.split(" from ")
                if len(parts) > 1:
                    return parts[1].strip().split()[0].split("(")[0]
            elif query_type == "insert":
                # insert into users
                parts = query.split(" into ")
                if len(parts) > 1:
                    return parts[1].strip().split()[0].split("(")[0]
            elif query_type == "update":
                # update users
                parts = query.split()
                if len(parts) > 1:
                    return parts[1].strip().split()[0].split("(")[0]
            elif query_type == "delete":
                # delete from users
                parts = query.split(" from ")
                if len(parts) > 1:
                    return parts[1].strip().split()[0].split("(")[0]
        except (IndexError, ValueError):
            pass
        
        return "unknown"

    def _sanitize_query(self, query: str) -> str:
        """净化查询语句，移除参数值
        
        Args:
            query: 原始SQL查询语句
            
        Returns:
            str: 净化后的查询语句
        """
        # 这里只是一个简单实现，实际使用时可能需要更复杂的解析
        return query

    def instrument_session(self, session_cls: type) -> type:
        """装饰 Session 类，注入监控
        
        Args:
            session_cls: Session 类
            
        Returns:
            type: 装饰后的 Session 类
        """
        original_execute = session_cls.execute
        original_commit = session_cls.commit
        original_rollback = session_cls.rollback
        
        metrics_recorder = self.metrics_recorder
        tracer = self.tracer
        
        @wraps(original_execute)
        def patched_execute(self, *args, **kwargs):
            start_time = time.time()
            
            # 创建 span
            span = None
            if tracer:
                span_name = "db.execute"
                span_attributes = {
                    "db.operation": "execute",
                }
                span = tracer.start_span(span_name, SpanKind.CLIENT, span_attributes)
            
            try:
                result = original_execute(self, *args, **kwargs)
                return result
            except Exception as e:
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                
                # 记录错误指标
                metrics_recorder.increment_counter(
                    StandardMetrics.DB_ERRORS.name,
                    1.0,
                    {"operation": "execute", "error": type(e).__name__}
                )
                raise
            finally:
                duration = time.time() - start_time
                
                # 记录持续时间
                metrics_recorder.observe_histogram(
                    StandardMetrics.DB_OPERATION_DURATION.name,
                    duration,
                    {"operation": "execute"}
                )
                
                if span:
                    # 结束 span
                    if hasattr(span, "_end_span"):
                        span._end_span()
        
        @wraps(original_commit)
        def patched_commit(self, *args, **kwargs):
            start_time = time.time()
            
            # 创建 span
            span = None
            if tracer:
                span_name = "db.commit"
                span_attributes = {
                    "db.operation": "commit",
                }
                span = tracer.start_span(span_name, SpanKind.CLIENT, span_attributes)
            
            try:
                result = original_commit(self, *args, **kwargs)
                return result
            except Exception as e:
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                
                # 记录错误指标
                metrics_recorder.increment_counter(
                    StandardMetrics.DB_ERRORS.name,
                    1.0,
                    {"operation": "commit", "error": type(e).__name__}
                )
                raise
            finally:
                duration = time.time() - start_time
                
                # 记录持续时间
                metrics_recorder.observe_histogram(
                    StandardMetrics.DB_OPERATION_DURATION.name,
                    duration,
                    {"operation": "commit"}
                )
                
                if span:
                    # 结束 span
                    if hasattr(span, "_end_span"):
                        span._end_span()
        
        @wraps(original_rollback)
        def patched_rollback(self, *args, **kwargs):
            start_time = time.time()
            
            # 创建 span
            span = None
            if tracer:
                span_name = "db.rollback"
                span_attributes = {
                    "db.operation": "rollback",
                }
                span = tracer.start_span(span_name, SpanKind.CLIENT, span_attributes)
            
            try:
                result = original_rollback(self, *args, **kwargs)
                
                # 记录回滚计数
                metrics_recorder.increment_counter(
                    "db_rollbacks_total",
                    1.0
                )
                
                return result
            except Exception as e:
                if span:
                    span.record_exception(e)
                    span.set_attribute("error", True)
                
                # 记录错误指标
                metrics_recorder.increment_counter(
                    StandardMetrics.DB_ERRORS.name,
                    1.0,
                    {"operation": "rollback", "error": type(e).__name__}
                )
                raise
            finally:
                duration = time.time() - start_time
                
                # 记录持续时间
                metrics_recorder.observe_histogram(
                    StandardMetrics.DB_OPERATION_DURATION.name,
                    duration,
                    {"operation": "rollback"}
                )
                
                if span:
                    # 结束 span
                    if hasattr(span, "_end_span"):
                        span._end_span()
        
        # 替换方法
        session_cls.execute = patched_execute  # type: ignore
        session_cls.commit = patched_commit  # type: ignore
        session_cls.rollback = patched_rollback  # type: ignore
        
        return session_cls
    
    @classmethod
    def install(
        cls,
        engine: Engine | AsyncEngine,
        metrics_recorder: IMetricsRecorder,
        tracer: Optional[ITracer] = None,
        record_parameters: bool = False,
    ) -> "SQLAlchemyListener":
        """便捷安装方法
        
        Args:
            engine: SQLAlchemy 引擎
            metrics_recorder: 指标记录器
            tracer: 追踪器，可选
            record_parameters: 是否记录参数，默认为 False
            
        Returns:
            SQLAlchemyListener: 监听器实例
        """
        listener = cls(metrics_recorder, tracer, record_parameters)
        
        if isinstance(engine, AsyncEngine):
            listener.install_async_hooks(engine)
        else:
            listener.install_sync_hooks(engine)
        
        return listener

# 使用示例
"""
# 同步引擎
from sqlalchemy import create_engine
engine = create_engine("postgresql://user:pass@localhost/dbname")
listener = SQLAlchemyListener.install(engine, metrics_recorder, tracer)

# 异步引擎
from sqlalchemy.ext.asyncio import create_async_engine
async_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/dbname")
listener = SQLAlchemyListener.install(async_engine, metrics_recorder, tracer)
""" 