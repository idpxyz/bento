"""Schema 注册监控模块

该模块用于监控 Schema 注册的情况，记录日志并提供健康检查功能。
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
import structlog
from pydantic import BaseModel, Field

from idp.framework.infrastructure.logger.manager import logger_manager
from idp.framework.infrastructure.schema.cli.schemactl import SCHEMA_DIR, load_registry


class SchemaStatus(BaseModel):
    """Schema 状态模型"""
    schema_name: str
    topic: str
    format: str
    type: Optional[str] = None
    version: Optional[int] = None
    status: str
    error: Optional[str] = None
    status_code: Optional[int] = None
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MonitorResult(BaseModel):
    """监控结果模型"""
    healthy: bool
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    results: List[SchemaStatus]


class SchemaRegistry(BaseModel):
    """Schema 注册表模型"""
    schemas: List[Dict[str, Any]]
    total_schemas: int = Field(0)
    schema_types: Dict[str, int] = Field(default_factory=dict)
    namespaces: List[str] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        self.total_schemas = len(self.schemas)
        self._calculate_stats()

    def _calculate_stats(self):
        """计算注册表统计信息"""
        self.schema_types = {}
        namespaces = set()
        
        for schema in self.schemas:
            # 统计 schema 类型
            schema_format = schema.get('format')
            if schema_format:
                self.schema_types[schema_format] = self.schema_types.get(schema_format, 0) + 1
            
            # 收集命名空间
            topic = schema.get('topic', '')
            if topic:
                parts = topic.replace('persistent://', '').split('/')
                if len(parts) >= 2:
                    namespaces.add(f"{parts[0]}/{parts[1]}")
        
        self.namespaces = sorted(list(namespaces))


class SchemaRegistrationMetrics(BaseModel):
    """Schema 注册指标模型"""
    success_count: int = 0
    error_count: int = 0
    total_count: int = Field(0)
    success_rate: float = Field(0.0)
    schema_types: Dict[str, int] = Field(default_factory=dict)
    error_types: Optional[Dict[str, int]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def __init__(self, **data):
        super().__init__(**data)
        self.total_count = self.success_count + self.error_count
        if self.total_count > 0:
            self.success_rate = self.success_count / self.total_count


class SchemaMetricsCollector:
    """Schema 指标收集器"""
    
    def __init__(self):
        self.metrics_dir = os.path.join(SCHEMA_DIR, "monitor", "metrics")
        os.makedirs(self.metrics_dir, exist_ok=True)
        
    def save_metrics(self, metrics: SchemaRegistrationMetrics) -> None:
        """保存指标数据到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = os.path.join(self.metrics_dir, f"schema_metrics_{timestamp}.json")
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics.dict(), f, indent=2, ensure_ascii=False)
            
    def load_metrics(self, days: int = 7) -> List[SchemaRegistrationMetrics]:
        """加载指定天数的指标数据"""
        if not os.path.exists(self.metrics_dir):
            return []
            
        metrics_files = []
        for file in os.listdir(self.metrics_dir):
            if file.startswith("schema_metrics_") and file.endswith(".json"):
                metrics_files.append(os.path.join(self.metrics_dir, file))
                
        # 按时间倒序排序
        metrics_files.sort(reverse=True)
        
        # 计算截止时间
        cutoff_time = datetime.now() - timedelta(days=days)
        
        metrics = []
        for file_path in metrics_files:
            try:
                # 从文件名获取时间戳
                timestamp_str = os.path.basename(file_path).replace("schema_metrics_", "").replace(".json", "")
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                # 如果文件时间早于截止时间，跳过
                if file_time < cutoff_time:
                    continue
                    
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    metrics.append(SchemaRegistrationMetrics(**data))
            except Exception as e:
                logger.error(f"加载指标文件失败: {file_path}", exc_info=e)
                continue
                
        return metrics

    def collect_metrics(self, monitor_result: MonitorResult) -> SchemaRegistrationMetrics:
        """从监控结果中收集指标"""
        success_count = 0
        error_count = 0
        schema_types = {}
        error_types = {}
        
        for result in monitor_result.results:
            if result.status == "available" and result.status_code == 200:
                success_count += 1
                schema_type = result.type or result.format
                schema_types[schema_type] = schema_types.get(schema_type, 0) + 1
            else:
                error_count += 1
                error_type = result.error or "unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        metrics = SchemaRegistrationMetrics(
            success_count=success_count,
            error_count=error_count,
            schema_types=schema_types,
            error_types=error_types if error_count > 0 else None,
            timestamp=monitor_result.timestamp
        )
        
        # 保存指标
        self.save_metrics(metrics)
        
        return metrics


class SchemaMonitor:
    """Schema 注册监控"""
    
    def __init__(self, pulsar_admin_url: Optional[str] = None):
        """初始化 Schema 监控器
        
        Args:
            pulsar_admin_url: Pulsar Admin URL，如果为空则尝试从环境变量获取
        """
        self.pulsar_admin_url = pulsar_admin_url or os.environ.get("PULSAR_ADMIN_URL")
        self.logger = logger_manager.get_logger(__name__)
        self.metrics_collector = SchemaMetricsCollector()
        
        # 绑定上下文
        logger_manager.bind_context(
            component="schema_registry",
            subsystem="monitoring"
        )
    
    async def check_schema_health(self) -> MonitorResult:
        """检查 Schema 健康状态
        
        返回:
            MonitorResult: 监控结果
        """
        if not self.pulsar_admin_url:
            self.logger.error("未指定 Pulsar Admin URL", error_type="configuration")
            return MonitorResult(healthy=False, results=[])
        
        registry = load_registry()
        healthy = True
        results: List[SchemaStatus] = []
        
        for schema in registry.get('schemas', []):
            schema_name = schema.get('name')
            schema_format = schema.get('format')
            topic = schema.get('topic')
            
            if not all([schema_name, schema_format, topic]):
                self.logger.warning(
                    "跳过不完整的 schema 定义", 
                    schema_name=schema_name,
                    event_type="schema_monitoring",
                    action="skip"
                )
                continue
            
            # 解析 topic
            topic_parts = topic.replace("persistent://", "").split("/")
            if len(topic_parts) != 3:
                self.logger.warning(
                    "无效的 topic 格式", 
                    schema_name=schema_name, 
                    topic=topic,
                    event_type="schema_monitoring",
                    action="skip"
                )
                continue
            
            tenant, namespace, topic_name = topic_parts
            
            # 构建 Schema URL
            url = f"{self.pulsar_admin_url}/admin/v2/schemas/{tenant}/{namespace}/{topic_name}/schema"
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        status_code = response.status
                        if status_code == 200:
                            data = await response.json()
                            schema_status = SchemaStatus(
                                schema_name=schema_name,
                                topic=topic,
                                format=schema_format,
                                type=data.get('type'),
                                version=data.get('version'),
                                status="available",
                                status_code=status_code
                            )
                        else:
                            error_text = await response.text()
                            schema_status = SchemaStatus(
                                schema_name=schema_name,
                                topic=topic,
                                format=schema_format,
                                status="unavailable",
                                error=error_text,
                                status_code=status_code
                            )
                            healthy = False
                            
                        results.append(schema_status)
                        
            except Exception as e:
                self.logger.error(
                    "检查 Schema 健康状态出错",
                    schema_name=schema_name,
                    topic=topic,
                    schema_format=schema_format,
                    error=f"{url} {str(e)}",
                    error_type="check_failed",
                    event_type="schema_monitoring",
                    action="health_check"
                )
                
                results.append(SchemaStatus(
                    schema_name=schema_name,
                    topic=topic,
                    format=schema_format,
                    status="error",
                    error=str(e)
                ))
                healthy = False
        
        monitor_result = MonitorResult(healthy=healthy, results=results)
        
        # 收集并保存指标
        try:
            self.metrics_collector.collect_metrics(monitor_result)
        except Exception as e:
            self.logger.error("收集指标失败", error=str(e), error_type="metrics_collection_failed")
        
        return monitor_result
    
    def log_registration_result(self, 
                               schema_name: str, 
                               topic: str, 
                               schema_format: str, 
                               schema_type: str,
                               success: bool, 
                               error_msg: Optional[str] = None,
                               status_code: Optional[int] = None,
                               duration_ms: Optional[float] = None) -> None:
        """记录 Schema 注册结果
        
        Args:
            schema_name: Schema 名称
            topic: Topic 名称
            schema_format: Schema 格式 (json, proto, avro)
            schema_type: Schema 类型 (JSON, PROTOBUF, AVRO)
            success: 是否成功
            error_msg: 错误信息
            status_code: HTTP 状态码
            duration_ms: 持续时间(毫秒)
        """
        log_context = {
            "schema_name": schema_name,
            "topic": topic,
            "schema_format": schema_format,
            "schema_type": schema_type,
            "event_type": "schema_registration",
            "success": success
        }
        
        if status_code is not None:
            log_context["status_code"] = status_code
            
        if duration_ms is not None:
            log_context["duration_ms"] = duration_ms
            
        if success:
            self.logger.info(
                "Schema 注册成功",
                **log_context
            )
        else:
            log_context["error"] = error_msg
            
            error_type = "unknown"
            if status_code == 409:
                error_type = "conflict"
            elif status_code == 422:
                error_type = "validation"
                
            log_context["error_type"] = error_type
            
            self.logger.error(
                "Schema 注册失败",
                **log_context
            )
    
    def log_registration_summary(self, 
                                success_count: int, 
                                error_count: int, 
                                success_schemas: List[str], 
                                error_schemas: Dict[str, str],
                                total_duration_ms: Optional[float] = None) -> None:
        """记录 Schema 注册汇总信息
        
        Args:
            success_count: 成功数量
            error_count: 失败数量
            success_schemas: 成功的 Schema 列表
            error_schemas: 失败的 Schema 及错误信息
            total_duration_ms: 总持续时间(毫秒)
        """
        log_context = {
            "success_count": success_count,
            "error_count": error_count,
            "total_count": success_count + error_count,
            "success_rate": success_count / (success_count + error_count) if (success_count + error_count) > 0 else 0,
            "event_type": "schema_registration_summary",
        }
        
        if total_duration_ms is not None:
            log_context["total_duration_ms"] = total_duration_ms
            
        if success_schemas:
            log_context["success_schemas"] = success_schemas
            
        if error_schemas:
            log_context["error_schemas"] = [
                {"name": name, "error": error} 
                for name, error in error_schemas.items()
            ]
            
        if error_count > 0:
            self.logger.warning(
                "Schema 注册完成，有失败项",
                **log_context
            )
        else:
            self.logger.info(
                "Schema 注册全部成功",
                **log_context
            )
    
    def collect_metrics(self, 
                       registry: Dict[str, Any], 
                       success_schemas: List[str], 
                       error_schemas: Dict[str, str]) -> Dict[str, Any]:
        """收集 Schema 注册指标
        
        Args:
            registry: Schema 注册表
            success_schemas: 成功的 Schema 列表
            error_schemas: 失败的 Schema 及错误信息
            
        Returns:
            Dict[str, Any]: Schema 注册指标
        """
        total_schemas = len(registry.get('schemas', []))
        success_count = len(success_schemas)
        error_count = len(error_schemas)
        
        # 统计各类型 Schema 数量
        schema_types = {}
        for schema in registry.get('schemas', []):
            schema_format = schema.get('format')
            schema_types[schema_format] = schema_types.get(schema_format, 0) + 1
        
        # 统计错误类型
        error_types = {}
        for schema_name, error_msg in error_schemas.items():
            error_type = "unknown"
            if "409" in error_msg:
                error_type = "conflict"
            elif "422" in error_msg:
                error_type = "validation"
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        metrics = {
            "total_schemas": total_schemas,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / total_schemas if total_schemas > 0 else 0,
            "schema_types": schema_types,
            "error_types": error_types,
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录指标
        self.logger.info(
            "Schema 注册指标",
            event_type="schema_metrics",
            **metrics
        )
        
        return metrics
    
    async def monitor_registration(self) -> None:
        """监控 Schema 注册
        
        这个方法会定期检查 Schema 的健康状态并记录日志
        """
        while True:
            try:
                result = await self.check_schema_health()
                
                # 导出结果到文件
                monitor_dir = os.path.join(SCHEMA_DIR, "monitor")
                os.makedirs(monitor_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = os.path.join(monitor_dir, f"schema_health_{timestamp}.json")
                
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "timestamp": result.timestamp,
                        "healthy": result.healthy,
                        "results": [r.dict() for r in result.results]
                    }, f, indent=2, ensure_ascii=False)
                
                # 等待一段时间再次检查
                await asyncio.sleep(3600)  # 默认每小时检查一次
                
            except Exception as e:
                self.logger.error(
                    "Schema 监控出错",
                    error=str(e),
                    event_type="schema_monitoring",
                    action="monitor_registration",
                    error_type="monitor_failed",
                    exc_info=True
                )
                await asyncio.sleep(300)  # 出错后等待5分钟再次尝试
    
    async def start_monitoring(self) -> None:
        """启动 Schema 监控
        
        这个方法会创建一个后台任务监控 Schema 注册
        """
        # 立即执行一次健康检查
        await self.check_schema_health()
        
        # 启动持续监控
        asyncio.create_task(self.monitor_registration())
        
        self.logger.info(
            "Schema 监控已启动",
            event_type="schema_monitoring",
            action="start_monitoring"
        )


# 创建全局 Schema 监控器实例
schema_monitor = SchemaMonitor() 