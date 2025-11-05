"""
简化的异常处理演示

展示IDP框架中简化后的异常处理用法，包括：
1. 使用函数式异常工厂
2. 简化的异常创建流程
3. 异步背景任务中的异常处理
"""

import asyncio
import random
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Request
from pydantic import BaseModel

from idp.framework.exception import (
    AsyncTaskExceptionMiddleware,
    DomainException,
    app_exception,
    background_task_context,
    background_task_handler,
    common_error_response,
    domain_exception,
    infra_exception,
    register_exception_handlers,
)
from idp.framework.exception.code.common import CommonErrorCode
from idp.framework.exception.demo.request_context import TraceIDMiddleware

app = FastAPI(title="简化异常处理演示")

# 注册中间件和异常处理器
app.add_middleware(TraceIDMiddleware)
register_exception_handlers(app)


# 模拟异步操作
async def fetch_user_data(user_id: int):
    """模拟异步获取用户数据"""
    await asyncio.sleep(0.5)  # 模拟网络延迟
    
    # 直接使用工厂函数创建异常
    if random.random() < 0.3:
        raise domain_exception(
            code=CommonErrorCode.RESOURCE_NOT_FOUND, 
            details={"user_id": user_id}
        )
    
    return {"id": user_id, "name": f"User {user_id}", "active": True}


class UserNotification(BaseModel):
    """用户通知模型"""
    user_id: int
    message: str
    priority: str = "normal"


# 1. 路由异常处理示例
@app.get(
    "/users/{user_id}",
    responses=common_error_response,
    summary="获取用户信息",
    description="演示简化的异常创建和处理"
)
async def get_user(user_id: int):
    """通过ID获取用户信息
    
    此路由演示了如何使用简化的异常工厂函数
    """
    try:
        return await fetch_user_data(user_id)
    except DomainException:
        # 已经是IDP异常，直接重新抛出
        raise
    except Exception as e:
        # 包装为IDP异常
        raise infra_exception(
            code=CommonErrorCode.UNKNOWN_ERROR,
            details={"operation": "get_user"},
            cause=e
        )


# 2. 后台任务示例
@app.post(
    "/notifications/send",
    responses=common_error_response,
    summary="发送用户通知",
    description="演示后台任务中的异常处理"
)
async def send_notification(
    notification: UserNotification, 
    background_tasks: BackgroundTasks
):
    """发送通知到用户
    
    此路由演示了如何在后台任务中使用异常处理
    """
    # 检查用户是否存在
    try:
        user = await fetch_user_data(notification.user_id)
    except Exception as e:
        # 创建并抛出应用异常
        raise app_exception(
            code=CommonErrorCode.INVALID_PARAMS,
            details={"notification": notification.model_dump()},
            cause=e
        )
    
    # 添加带有异步异常处理的后台任务
    background_tasks.add_task(
        AsyncTaskExceptionMiddleware.wrap_task(
            process_notification,
            task_name=f"send_notification_{notification.user_id}",
            error_code=CommonErrorCode.RESOURCE_CONFLICT
        ),
        notification=notification,
        user=user
    )
    
    return {"status": "notification queued", "user_id": user["id"]}


# 异步后台任务函数
async def process_notification(notification: UserNotification, user: Dict):
    """处理通知发送
    
    此函数使用异步上下文管理器处理异常
    """
    print(f"开始发送通知到用户 {user['name']}")
    
    # 使用异步上下文管理器处理异常
    async with background_task_context(
        task_name=f"process_notification_{notification.user_id}",
        error_code=CommonErrorCode.OPERATION_FAILED
    ):
        # 模拟第三方通知服务调用
        await asyncio.sleep(1.0)
        
        # 模拟随机错误
        if random.random() < 0.2:
            raise infra_exception(
                code=CommonErrorCode.SERVICE_UNAVAILABLE,
                details={"service": "notification_service"}
            )
        
        # 模拟处理结果
        print(f"通知发送成功: {notification.message} 到 {user['name']}")
    
    print(f"通知处理完成: {notification.user_id}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "idp.framework.exception.demo.simplified_demo:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    ) 