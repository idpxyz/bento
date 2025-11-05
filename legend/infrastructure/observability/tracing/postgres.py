"""
PostgreSQL链路追踪实现

该实现将链路追踪数据持久化存储到PostgreSQL数据库中，支持长期数据保留和历史查询。
"""
import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncContextManager, Dict, List, Optional, Union, cast

import asyncpg
from pydantic import BaseModel, Field

from ..core import Span, SpanKind
from .tracer import BaseSpan, BaseTracer

logger = logging.getLogger(__name__)

class PostgresTracingConfig(BaseModel):
    """PostgreSQL链路追踪配置"""
    connection_string: str = Field(..., description="PostgreSQL连接字符串")
    spans_table_name: str = Field(default="observability_spans", description="Span表名")
    events_table_name: str = Field(default="observability_span_events", description="Span事件表名")
    schema_name: str = Field(default="public", description="数据库Schema")
    retention_days: int = Field(default=30, description="数据保留天数")
    batch_size: int = Field(default=100, description="批量插入大小")
    flush_interval: float = Field(default=5.0, description="强制刷新间隔(秒)")

class PostgresSpan(BaseSpan):
    """PostgreSQL Span实现"""
    
    def __init__(
        self,
        name: str,
        tracer: "PostgresTracer",
        kind: SpanKind = SpanKind.INTERNAL,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        """初始化Span
        
        Args:
            name: Span名称
            tracer: 追踪器实例
            kind: Span类型
            trace_id: 追踪ID，如果为None则生成新的
            parent_span_id: 父Span ID，如果为None则为根Span
        """
        super().__init__(name, trace_id, parent_span_id)
        self._tracer = tracer
        self._kind = kind
        self._is_exported = False
    
    @property
    def kind(self) -> SpanKind:
        """获取Span类型"""
        return self._kind
    
    def end(self) -> None:
        """结束Span"""
        if self._end_time is None:
            super().end()
            self._export()
    
    def _export(self) -> None:
        """导出Span到缓存，等待刷新到PostgreSQL"""
        if self._is_exported:
            return
            
        self._is_exported = True
        self._tracer._add_span_to_cache(self.to_dict())
    
    def to_dict(self) -> Dict[str, Any]:
        """将Span转换为字典
        
        Returns:
            Dict[str, Any]: Span字典表示
        """
        return {
            "name": self._name,
            "trace_id": self._trace_id,
            "span_id": self._span_id,
            "parent_span_id": self._parent_span_id,
            "kind": self._kind.value,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "duration": self.duration,
            "status": self._status,
            "status_message": self._status_message,
            "attributes": self._attributes,
            "events": self._events,
            "service_name": self._tracer.service_name
        }
    
    def __str__(self) -> str:
        """获取字符串表示
        
        Returns:
            str: Span的字符串表示
        """
        return (
            f"PostgresSpan(name={self._name}, trace_id={self._trace_id}, "
            f"span_id={self._span_id}, parent_span_id={self._parent_span_id}, "
            f"duration={self.duration}s)"
        )

class PostgresTracer(BaseTracer):
    """PostgreSQL追踪器实现
    
    将链路追踪数据持久化到PostgreSQL数据库中，便于长期存储和历史分析。
    """
    
    def __init__(
        self,
        service_name: str,
        connection_string: str,
        sample_rate: float = 1.0,
        spans_table_name: str = "observability_spans",
        events_table_name: str = "observability_span_events",
        schema_name: str = "public",
        retention_days: int = 30,
        batch_size: int = 100,
        flush_interval: float = 5.0
    ):
        """初始化PostgreSQL追踪器
        
        Args:
            service_name: 服务名称
            connection_string: PostgreSQL连接字符串
            sample_rate: 采样率(0.0-1.0)
            spans_table_name: Span表名
            events_table_name: Span事件表名
            schema_name: 数据库Schema
            retention_days: 数据保留天数
            batch_size: 批量插入大小
            flush_interval: 强制刷新间隔(秒)
        """
        super().__init__(service_name, sample_rate)
        
        # 初始化连接相关变量
        self.connection_string = connection_string
        self.spans_table_name = f"{schema_name}.{spans_table_name}"
        self.events_table_name = f"{schema_name}.{events_table_name}"
        self.schema_name = schema_name
        self.retention_days = retention_days
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # 连接池
        self._pool: Optional[asyncpg.Pool] = None
        
        # 缓存和状态
        self._spans_cache: List[Dict[str, Any]] = []
        self._events_cache: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._is_flushing = False
        
        # 统计信息
        self._spans_exported = 0
        self._spans_dropped = 0
        
        logger.info("PostgreSQL tracer initialized")
    
    async def initialize(self) -> None:
        """初始化数据库连接和表结构"""
        try:
            # 创建连接池
            self._pool = await asyncpg.create_pool(self.connection_string)
            
            # 创建表结构
            async with self._pool.acquire() as conn:
                # 确保schema存在
                if self.schema_name != "public":
                    await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
                
                # 创建span表
                await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.spans_table_name} (
                    id SERIAL PRIMARY KEY,
                    trace_id VARCHAR(36) NOT NULL,
                    span_id VARCHAR(36) NOT NULL,
                    parent_span_id VARCHAR(36),
                    name VARCHAR(255) NOT NULL,
                    kind VARCHAR(50) NOT NULL,
                    service_name VARCHAR(100) NOT NULL,
                    start_time DOUBLE PRECISION NOT NULL,
                    end_time DOUBLE PRECISION,
                    duration DOUBLE PRECISION,
                    status VARCHAR(50) NOT NULL,
                    status_message TEXT,
                    attributes JSONB,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (trace_id, span_id),
                    INDEX idx_spans_trace_id (trace_id),
                    INDEX idx_spans_timestamp (timestamp)
                )
                """)
                
                # 创建span事件表
                await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.events_table_name} (
                    id SERIAL PRIMARY KEY,
                    trace_id VARCHAR(36) NOT NULL,
                    span_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    timestamp DOUBLE PRECISION NOT NULL,
                    attributes JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_span_events_span_id (span_id),
                    INDEX idx_span_events_trace_id (trace_id)
                )
                """)
            
            # 启动定期刷新任务
            self._start_periodic_flush()
            
            # 设置定期清理任务
            if self.retention_days > 0:
                asyncio.create_task(self._periodic_cleanup())
                
            logger.info(f"PostgreSQL tracer tables initialized: {self.spans_table_name}, {self.events_table_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL tracer: {e}")
            if self._pool:
                await self._pool.close()
                self._pool = None
            raise
    
    def _start_periodic_flush(self) -> None:
        """启动定期刷新任务"""
        if self._flush_task is not None:
            self._flush_task.cancel()
        
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.debug("Started periodic flush task")
    
    async def _periodic_flush(self) -> None:
        """定期刷新缓存的Span数据"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
                await asyncio.sleep(1.0)  # 错误后短暂暂停
    
    async def _periodic_cleanup(self) -> None:
        """定期清理过期数据"""
        while True:
            try:
                await asyncio.sleep(24 * 60 * 60)  # 每天执行一次
                if self._pool:
                    async with self._pool.acquire() as conn:
                        # 清理span表
                        await conn.execute(
                            f"""
                            DELETE FROM {self.spans_table_name} 
                            WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '{self.retention_days} days'
                            """
                        )
                        # 清理事件表
                        await conn.execute(
                            f"""
                            DELETE FROM {self.events_table_name} 
                            WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '{self.retention_days} days'
                            """
                        )
                        logger.info(f"Cleaned up spans and events older than {self.retention_days} days")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # 错误后短暂暂停
    
    def _add_span_to_cache(self, span_dict: Dict[str, Any]) -> None:
        """添加Span数据到缓存
        
        Args:
            span_dict: Span字典表示
        """
        if len(self._spans_cache) >= self.batch_size * 2:
            self._spans_dropped += 1
            logger.warning("Spans cache full, dropping span")
            return
            
        # 添加基本的span数据到spans缓存
        span_data = {
            "trace_id": span_dict["trace_id"],
            "span_id": span_dict["span_id"],
            "parent_span_id": span_dict["parent_span_id"],
            "name": span_dict["name"],
            "kind": span_dict["kind"],
            "service_name": span_dict["service_name"],
            "start_time": span_dict["start_time"],
            "end_time": span_dict["end_time"],
            "duration": span_dict["duration"],
            "status": span_dict["status"],
            "status_message": span_dict["status_message"],
            "attributes": json.dumps(span_dict["attributes"])
        }
        self._spans_cache.append(span_data)
        
        # 添加事件数据到events缓存
        for event in span_dict["events"]:
            event_data = {
                "trace_id": span_dict["trace_id"],
                "span_id": span_dict["span_id"],
                "name": event["name"],
                "timestamp": event["timestamp"],
                "attributes": json.dumps(event.get("attributes", {}))
            }
            self._events_cache.append(event_data)
        
        # 如果缓存已满，触发刷新
        if len(self._spans_cache) >= self.batch_size:
            asyncio.create_task(self.flush())
    
    async def flush(self) -> None:
        """刷新缓存的Span数据到数据库"""
        if (not self._spans_cache and not self._events_cache) or self._is_flushing:
            return
            
        async with self._lock:
            if (not self._spans_cache and not self._events_cache) or self._is_flushing:
                return
                
            self._is_flushing = True
            try:
                spans_to_flush = self._spans_cache.copy()
                events_to_flush = self._events_cache.copy()
                self._spans_cache.clear()
                self._events_cache.clear()
                
                await self._flush_to_db(spans_to_flush, events_to_flush)
                self._spans_exported += len(spans_to_flush)
            except Exception as e:
                logger.error(f"Error flushing spans: {e}")
                # 失败时将数据放回缓存
                self._spans_cache.extend(spans_to_flush)
                self._events_cache.extend(events_to_flush)
            finally:
                self._is_flushing = False
    
    async def _flush_to_db(self, spans: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> None:
        """将数据刷新到PostgreSQL
        
        Args:
            spans: Span数据列表
            events: 事件数据列表
        """
        if not spans and not events:
            return
            
        if not self._pool:
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize database connection for flushing: {e}")
                return
                
        try:
            if not self._pool:
                logger.error("Cannot flush spans: database connection not available")
                return
                
            async with self._pool.acquire() as conn:
                # 插入span数据
                if spans:
                    span_values = []
                    for span in spans:
                        span_values.append((
                            span["trace_id"],
                            span["span_id"],
                            span["parent_span_id"],
                            span["name"],
                            span["kind"],
                            span["service_name"],
                            span["start_time"],
                            span["end_time"],
                            span["duration"],
                            span["status"],
                            span["status_message"],
                            span["attributes"]
                        ))
                        
                    await conn.executemany(
                        f"""
                        INSERT INTO {self.spans_table_name}
                        (trace_id, span_id, parent_span_id, name, kind, service_name, 
                         start_time, end_time, duration, status, status_message, attributes)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (trace_id, span_id) DO UPDATE
                        SET end_time = $8,
                            duration = $9,
                            status = $10,
                            status_message = $11,
                            attributes = $12
                        """,
                        span_values
                    )
                
                # 插入事件数据
                if events:
                    event_values = []
                    for event in events:
                        event_values.append((
                            event["trace_id"],
                            event["span_id"],
                            event["name"],
                            event["timestamp"],
                            event["attributes"]
                        ))
                        
                    await conn.executemany(
                        f"""
                        INSERT INTO {self.events_table_name}
                        (trace_id, span_id, name, timestamp, attributes)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        event_values
                    )
                    
            logger.debug(f"Flushed {len(spans)} spans and {len(events)} events to PostgreSQL")
            
        except Exception as e:
            logger.error(f"Error flushing data to PostgreSQL: {e}")
            # 连接错误时尝试重新初始化
            if isinstance(e, asyncpg.exceptions.ConnectionDoesNotExistError):
                self._pool = None
    
    async def close(self) -> None:
        """关闭连接池并清理资源"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
                
        await self.flush()  # 确保所有缓存的数据都被刷新
        
        if self._pool:
            await self._pool.close()
            self._pool = None
            
        logger.info("PostgreSQL tracer closed")
    
    async def _create_span(
        self, 
        name: str, 
        kind: SpanKind,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> Span:
        """创建新的Span
        
        Args:
            name: Span名称
            kind: Span类型
            trace_id: 追踪ID，如果为None则生成新的
            parent_span_id: 父Span ID，如果为None则为根Span
            
        Returns:
            Span: 新创建的Span
        """
        span = PostgresSpan(
            name=name,
            tracer=self,
            kind=kind,
            trace_id=trace_id,
            parent_span_id=parent_span_id
        )
        return cast(Span, span)
    
    async def _end_span(self, span: Span) -> None:
        """结束Span并导出
        
        Args:
            span: 要结束的Span
        """
        # PostgresSpan的end方法会自动导出，所以这里不需要额外操作
        pass
    
    async def health_check(self) -> bool:
        """健康检查
        
        Returns:
            bool: 数据库连接是否健康
        """
        try:
            if not self._pool:
                await self.initialize()
                
            if not self._pool:
                return False
                
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_trace(self, trace_id: str) -> Dict[str, Any]:
        """获取完整的追踪信息
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            Dict[str, Any]: 追踪信息，包含所有span和事件
        """
        if not self._pool:
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize database connection: {e}")
                return {"trace_id": trace_id, "spans": [], "events": []}
        
        try:
            if not self._pool:
                return {"trace_id": trace_id, "spans": [], "events": []}
                
            async with self._pool.acquire() as conn:
                # 获取所有span
                spans = await conn.fetch(
                    f"""
                    SELECT * FROM {self.spans_table_name}
                    WHERE trace_id = $1
                    ORDER BY start_time
                    """,
                    trace_id
                )
                
                # 获取所有事件
                events = await conn.fetch(
                    f"""
                    SELECT * FROM {self.events_table_name}
                    WHERE trace_id = $1
                    ORDER BY timestamp
                    """,
                    trace_id
                )
                
            # 转换为字典
            spans_dict = [
                {
                    "id": span["id"],
                    "trace_id": span["trace_id"],
                    "span_id": span["span_id"],
                    "parent_span_id": span["parent_span_id"],
                    "name": span["name"],
                    "kind": span["kind"],
                    "service_name": span["service_name"],
                    "start_time": span["start_time"],
                    "end_time": span["end_time"],
                    "duration": span["duration"],
                    "status": span["status"],
                    "status_message": span["status_message"],
                    "attributes": json.loads(span["attributes"]) if span["attributes"] else {},
                    "timestamp": span["timestamp"].isoformat() if span["timestamp"] else None
                }
                for span in spans
            ]
            
            events_dict = [
                {
                    "id": event["id"],
                    "trace_id": event["trace_id"],
                    "span_id": event["span_id"],
                    "name": event["name"],
                    "timestamp": event["timestamp"],
                    "attributes": json.loads(event["attributes"]) if event["attributes"] else {},
                    "created_at": event["created_at"].isoformat() if event["created_at"] else None
                }
                for event in events
            ]
            
            return {
                "trace_id": trace_id,
                "spans": spans_dict,
                "events": events_dict
            }
            
        except Exception as e:
            logger.error(f"Error retrieving trace {trace_id}: {e}")
            return {"trace_id": trace_id, "spans": [], "events": []}
    
    async def get_recent_traces(
        self,
        limit: int = 100,
        service_name: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """获取最近的追踪信息列表
        
        Args:
            limit: 返回结果数量限制，默认为100
            service_name: 按服务名称过滤，默认为None
            status: 按状态过滤，默认为None
            start_time: 开始时间，默认为None
            end_time: 结束时间，默认为None
            
        Returns:
            List[Dict[str, Any]]: 追踪信息列表
        """
        if not self._pool:
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize database connection: {e}")
                return []
        
        try:
            if not self._pool:
                return []
                
            query_parts = [
                f"""
                SELECT DISTINCT ON (trace_id) 
                trace_id, COUNT(span_id) OVER (PARTITION BY trace_id) as span_count,
                MIN(start_time) OVER (PARTITION BY trace_id) as trace_start_time,
                MAX(end_time) OVER (PARTITION BY trace_id) as trace_end_time,
                MAX(timestamp) OVER (PARTITION BY trace_id) as last_updated
                FROM {self.spans_table_name}
                WHERE 1=1
                """
            ]
            params: List[Any] = []
            
            if service_name:
                params.append(service_name)
                query_parts.append(f"AND service_name = ${len(params)}")
                
            if status:
                params.append(status)
                query_parts.append(f"AND status = ${len(params)}")
                
            if start_time:
                params.append(start_time)
                query_parts.append(f"AND timestamp >= ${len(params)}")
                
            if end_time:
                params.append(end_time)
                query_parts.append(f"AND timestamp <= ${len(params)}")
            
            query_parts.append("ORDER BY trace_id, last_updated DESC")
            query_parts.append(f"LIMIT ${len(params) + 1}")
            params.append(limit)
            
            query = " ".join(query_parts)
            
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
            return [
                {
                    "trace_id": row["trace_id"],
                    "span_count": row["span_count"],
                    "start_time": row["trace_start_time"],
                    "end_time": row["trace_end_time"],
                    "duration": row["trace_end_time"] - row["trace_start_time"] if row["trace_end_time"] and row["trace_start_time"] else None,
                    "last_updated": row["last_updated"].isoformat() if row["last_updated"] else None
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving recent traces: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取追踪器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "service_name": self.service_name,
            "sample_rate": self.sample_rate,
            "spans_exported": self._spans_exported,
            "spans_dropped": self._spans_dropped,
            "spans_pending": len(self._spans_cache),
            "events_pending": len(self._events_cache)
        }
        
    @classmethod
    def from_config(cls, config: PostgresTracingConfig, service_name: str, sample_rate: float = 1.0) -> "PostgresTracer":
        """从配置创建PostgreSQL追踪器
        
        Args:
            config: PostgreSQL配置
            service_name: 服务名称
            sample_rate: 采样率(0.0-1.0)
            
        Returns:
            PostgresTracer: PostgreSQL追踪器实例
        """
        return cls(
            service_name=service_name,
            connection_string=config.connection_string,
            sample_rate=sample_rate,
            spans_table_name=config.spans_table_name,
            events_table_name=config.events_table_name,
            schema_name=config.schema_name,
            retention_days=config.retention_days,
            batch_size=config.batch_size,
            flush_interval=config.flush_interval
        ) 