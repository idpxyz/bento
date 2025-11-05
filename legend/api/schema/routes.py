"""
Schema 注册监控 API 路由

该模块定义了 Schema 注册监控的 API 端点
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from idp.framework.infrastructure.schema.cli.schemactl import SCHEMA_DIR, load_registry
from idp.framework.infrastructure.schema.monitor.schema_monitor import (
    MonitorResult,
    SchemaMetricsCollector,
    SchemaMonitor,
    SchemaRegistrationMetrics,
    SchemaRegistry,
    SchemaStatus,
)

# 创建路由器
router = APIRouter(prefix="/schema-monitor", tags=["Schema Monitor"])

# 配置模板
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# 日志记录器
logger = logging.getLogger("schema-monitor-api")

# 数据模型
class ValidationRequest(BaseModel):
    """Schema验证请求模型"""
    data: Dict[str, Any]


class ValidationResponse(BaseModel):
    """Schema验证响应模型"""
    valid: bool
    errors: Optional[List[Dict[str, Any]]] = None


class CompatibilityRequest(BaseModel):
    """Schema兼容性检查请求模型"""
    schema_definition: Dict[str, Any]


class CompatibilityResponse(BaseModel):
    """Schema兼容性检查响应模型"""
    compatible: bool
    errors: Optional[List[Dict[str, Any]]] = None


# 依赖项
def get_schema_monitor(pulsar_admin_url: Optional[str] = Query(None, description="Pulsar Admin URL")) -> SchemaMonitor:
    """获取 Schema 监控器实例"""
    return SchemaMonitor(pulsar_admin_url)


def get_metrics_collector() -> SchemaMetricsCollector:
    """获取指标收集器实例"""
    return SchemaMetricsCollector()


# 页面路由
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Schema 监控仪表盘首页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Schema 注册监控"}
    )


@router.get("/schema/{schema_name}", response_class=HTMLResponse)
async def get_schema_detail_page(request: Request, schema_name: str):
    """返回Schema详情页面"""
    return templates.TemplateResponse(
        "schema_detail.html", 
        {"request": request, "title": f"Schema详情 - {schema_name}", "schema_name": schema_name}
    )


# API 路由
@router.get("/health", response_model=MonitorResult)
async def get_health(monitor: SchemaMonitor = Depends(get_schema_monitor)):
    """获取 Schema 健康状态"""
    try:
        return await monitor.check_schema_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查 Schema 健康状态失败: {str(e)}")


@router.get("/registry", response_model=SchemaRegistry)
async def get_registry():
    """获取 Schema 注册表信息"""
    try:
        registry = load_registry()
        return SchemaRegistry(schemas=registry.get('schemas', []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Schema 注册表失败: {str(e)}")


@router.get("/history", response_model=List[MonitorResult])
async def get_history(limit: int = Query(10, description="最大返回记录数")):
    """获取 Schema 健康检查历史记录"""
    try:
        monitor_dir = os.path.join(SCHEMA_DIR, "monitor")
        if not os.path.exists(monitor_dir):
            return []
        
        history_files = []
        for file in os.listdir(monitor_dir):
            if file.startswith("schema_health_") and file.endswith(".json"):
                history_files.append(os.path.join(monitor_dir, file))
        
        # 按时间倒序排序
        history_files.sort(reverse=True)
        history_files = history_files[:limit]
        
        history = []
        for file_path in history_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 将历史数据转换为 MonitorResult 模型
                    results = [
                        SchemaStatus(**result) 
                        for result in data.get("results", [])
                    ]
                    history.append(MonitorResult(
                        healthy=data.get("healthy", False),
                        timestamp=data.get("timestamp", datetime.now().isoformat()),
                        results=results
                    ))
            except Exception as e:
                logger.error(f"读取历史记录文件失败: {file_path}", exc_info=e)
                continue
        
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.post("/schema/{schema_name}/validate", response_model=ValidationResponse)
async def validate_schema_data(
    schema_name: str,
    request: ValidationRequest,
    monitor: SchemaMonitor = Depends(get_schema_monitor)
) -> ValidationResponse:
    """验证数据是否符合Schema定义"""
    try:
        # TODO: 实现Schema数据验证逻辑
        return ValidationResponse(valid=True)
    except Exception as e:
        return ValidationResponse(valid=False, errors=[{"message": str(e)}])


@router.post("/schema/{schema_name}/compatibility", response_model=CompatibilityResponse)
async def check_schema_compatibility(
    schema_name: str,
    request: CompatibilityRequest,
    monitor: SchemaMonitor = Depends(get_schema_monitor)
) -> CompatibilityResponse:
    """检查Schema兼容性"""
    try:
        # TODO: 实现Schema兼容性检查逻辑
        return CompatibilityResponse(compatible=True)
    except Exception as e:
        return CompatibilityResponse(compatible=False, errors=[{"message": str(e)}])


@router.get("/metrics", response_model=List[SchemaRegistrationMetrics])
async def get_metrics(
    days: int = Query(7, description="返回过去几天的指标数据"),
    collector: SchemaMetricsCollector = Depends(get_metrics_collector)
) -> List[SchemaRegistrationMetrics]:
    """获取 Schema 注册指标"""
    try:
        return collector.load_metrics(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}") 