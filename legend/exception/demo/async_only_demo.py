"""
完全异步异常处理演示

展示IDP框架中完全异步的异常处理用法，包括：
1. 使用异步异常工厂创建异常
2. 异步异常处理和上报
3. 异步背景任务中的异常处理
"""

import asyncio
import random
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from pydantic import BaseModel

from idp.framework.exception import (
    AsyncTaskExceptionMiddleware,
    DomainException,
    ErrorCode,
    ExceptionFactory,
    background_task_context,
    background_task_handler,
    common_error_response,
    exception_factory,
    register_exception_handlers,
)
from idp.framework.exception.code.common import CommonErrorCode
from idp.framework.exception.demo.request_context import TraceIDMiddleware

app = FastAPI(title="异步异常处理演示")

# 注册中间件和异常处理器
app.add_middleware(TraceIDMiddleware)
register_exception_handlers(app)


# 自定义异常工厂函数，封装工厂调用
async def create_error(
    code: ErrorCode, 
    details: Optional[Dict] = None,
    cause: Optional[Exception] = None
):
    """创建领域异常的便捷方法"""
    return await exception_factory.domain_exception(
        code=code, 
        details=details,
        cause=cause
    )


# 模拟异步操作
async def fetch_user_data(user_id: int):
    """模拟异步获取用户数据"""
    await asyncio.sleep(0.5)  # 模拟网络延迟
    
    # 异步创建和抛出异常
    if random.random() < 0.3:
        # 使用异步工厂创建异常
        error = await create_error(
            code=CommonErrorCode.RESOURCE_NOT_FOUND, 
            details={"user_id": user_id}
        )
        raise error
    
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
    description="演示异步异常创建和处理"
)
async def get_user(user_id: int):
    """通过ID获取用户信息
    
    此路由演示了如何使用异步工厂创建异常
    """
    try:
        return await fetch_user_data(user_id)
    except DomainException:
        # 已经是IDP异常，直接重新抛出
        raise
    except Exception as e:
        # 包装为IDP异常
        error = await exception_factory.infra_exception(
            code=CommonErrorCode.UNKNOWN_ERROR,
            details={"operation": "get_user"},
            cause=e
        )
        raise error


# 2. 后台任务示例
@app.post(
    "/notifications/send",
    responses=common_error_response,
    summary="发送用户通知",
    description="演示后台任务中的异步异常处理"
)
async def send_notification(
    notification: UserNotification, 
    background_tasks: BackgroundTasks
):
    """发送通知到用户
    
    此路由演示了如何在后台任务中使用异步异常处理
    """
    # 检查用户是否存在
    try:
        user = await fetch_user_data(notification.user_id)
    except Exception as e:
        # 创建并抛出应用异常
        error = await exception_factory.application_exception(
            code=CommonErrorCode.INVALID_PARAMS,
            details={"notification": notification.model_dump()},
            cause=e
        )
        raise error
    
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
            error = await exception_factory.infra_exception(
                code=CommonErrorCode.SERVICE_UNAVAILABLE,
                details={"service": "notification_service"}
            )
            raise error
        
        # 模拟处理结果
        print(f"通知发送成功: {notification.message} 到 {user['name']}")
    
    print(f"通知处理完成: {notification.user_id}")


# 3. 具有异步装饰器的定时任务
@background_task_handler(error_code=CommonErrorCode.OPERATION_FAILED)
async def cleanup_expired_notifications():
    """使用异步装饰器处理定时清理任务中的异常"""
    print("开始清理过期通知")
    await asyncio.sleep(1.0)
    
    # 随机模拟错误
    if random.random() < 0.3:
        db_error = ValueError("数据库连接失败")
        error = await exception_factory.infra_exception(
            code=CommonErrorCode.DATABASE_ERROR,
            details={"operation": "cleanup_expired_notifications"},
            cause=db_error
        )
        raise error
    
    print("清理通知完成")


@app.get("/tasks/cleanup")
async def trigger_cleanup():
    """触发清理任务
    
    此路由演示了带有异步装饰器的函数如何处理异常
    """
    try:
        await cleanup_expired_notifications()
        return {"message": "清理任务完成"}
    except Exception as e:
        # 异常已被处理器记录，但我们仍然可以创建特定的响应
        error = await exception_factory.application_exception(
            code=CommonErrorCode.OPERATION_FAILED,
            details={"task": "cleanup", "status": "failed"},
            cause=e
        )
        raise error


# 4. 依赖注入中的异步异常处理
async def validate_notification(payload: Dict):
    """依赖函数：验证通知数据
    
    此函数演示了在依赖注入中使用异步异常处理
    """
    priority = payload.get("priority", "")
    
    if priority not in ["low", "normal", "high", "urgent"]:
        # 使用异步工厂创建验证异常
        error = await exception_factory.application_exception(
            code=CommonErrorCode.INVALID_PARAMS,
            details={
                "priority": priority,
                "allowed_values": ["low", "normal", "high", "urgent"]
            }
        )
        raise error
    
    return payload


@app.post(
    "/notifications/validate",
    responses={
        **common_error_response,
        200: {"model": dict, "description": "通知验证成功"}
    }
)
async def validate_notification_endpoint(
    payload: Dict = Depends(validate_notification)
):
    """验证通知数据
    
    此路由演示了依赖注入中的异步异常处理
    """
    return {"status": "valid", "payload": payload}


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时设置定时任务"""
    asyncio.create_task(run_scheduled_tasks())


async def run_scheduled_tasks():
    """运行定时任务"""
    while True:
        try:
            await AsyncTaskExceptionMiddleware.execute_task(
                cleanup_expired_notifications,
                task_name="daily_cleanup"
            )
        except Exception:
            print("定时任务异常已被处理")
        
        await asyncio.sleep(30)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "idp.framework.exception.demo.async_only_demo:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    ) 