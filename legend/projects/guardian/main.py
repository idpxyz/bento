"""
Guardian API 应用入口点
"""

from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path

from idp.framework.auth import auth_router

# 从framework导入功能 - 使用安装的包而不是相对导入
from idp.framework.auth.utils import get_current_user

app = FastAPI(
    title="Guardian API",
    description="安全审计与策略执行服务",
    version="0.1.0",
)

app.include_router(auth_router)


@app.get("/")
async def root():
    """API 信息"""
    return {"service": "Guardian", "version": "0.1.0"}


@app.get("/audit-logs")
async def get_audit_logs():
    """获取审计日志示例"""
    # 这里只是一个示例，实际实现会从数据库或日志系统获取
    return [
        {
            "id": "1",
            "user": "admin",
            "action": "login",
            "timestamp": "2023-03-25T08:30:00Z",
        },
        {
            "id": "2",
            "user": "user1",
            "action": "view_document",
            "timestamp": "2023-03-25T08:35:00Z",
        },
    ]


@app.get("/policies")
async def get_policies():
    """获取安全策略列表"""
    # 示例数据
    return [
        {"id": "1", "name": "数据访问控制", "description": "控制敏感数据的访问权限"},
        {"id": "2", "name": "密码复杂度", "description": "强制执行密码复杂度要求"},
    ]


if __name__ == "__main__":
    import sys

    import uvicorn

    reload = "--reload" in sys.argv

    uvicorn.run(
        "main:app", host="0.0.0.0", port=6300, reload=reload, reload_dirs=["./"]
    )
