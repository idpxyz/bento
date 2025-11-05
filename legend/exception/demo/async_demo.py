"""
异步异常处理演示

展示IDP框架中各种异步异常处理的用法，包括：
1. FastAPI路由异常处理
2. 后台任务异常处理
3. 异步上下文管理器
4. 异步装饰器
"""

import asyncio
import random
from typing import List

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from pydantic import BaseModel

from idp.framework.exception import (
    AsyncTaskExceptionMiddleware,
    DomainException,
    ErrorCode,
    background_task_context,
    background_task_handler,
    common_error_response,
    domain_exception,
    register_exception_handlers,
)
from idp.framework.exception.code.common import CommonErrorCode
from idp.framework.exception.demo.request_context import TraceIDMiddleware

app = FastAPI()

# 注册中间件和异常处理器
app.add_middleware(TraceIDMiddleware)
register_exception_handlers(app)


# 模拟异步操作
async def fetch_user_data(user_id: int):
    """模拟获取用户数据"""
    await asyncio.sleep(0.5)  # 模拟网络延迟
    
    # 随机模拟错误
    if random.random() < 0.3:
        raise domain_exception(code=CommonErrorCode.RESOURCE_NOT_FOUND, details={"user_id": user_id})
    
    return {"id": user_id, "name": f"User {user_id}", "active": True}


async def process_items(items: List[dict]):
    """模拟处理多个数据项"""
    await asyncio.sleep(1.0)  # 模拟处理时间
    
    # 随机模拟错误
    if random.random() < 0.2:
        raise ValueError("处理数据时发生错误")
    
    return [{"processed": item} for item in items]


# 1. 路由异常处理示例
@app.get(
    "/users/{user_id}",
    responses=common_error_response,
    summary="获取用户信息",
    description="演示异步路由中的异常处理"
)
async def get_user(user_id: int):
    """通过ID获取用户信息
    
    此路由演示了路由函数中的异常会被自动捕获并返回标准化的错误响应
    """
    # 异常会被全局异常处理器捕获，转换为标准错误响应
    return await fetch_user_data(user_id)


# 2. 后台任务示例
@app.post(
    "/tasks/process",
    responses=common_error_response,
    summary="创建后台处理任务",
    description="演示后台任务中的异常处理"
)
async def create_task(background_tasks: BackgroundTasks):
    """创建一个后台处理任务
    
    此路由演示了如何处理后台任务中的异常
    """
    # 添加带有异常处理的后台任务
    background_tasks.add_task(
        AsyncTaskExceptionMiddleware.wrap_task(
            process_data,
            task_name="process_data_task",
            error_code=CommonErrorCode.RESOURCE_CONFLICT
        ),
        task_id=random.randint(1000, 9999)
    )
    
    return {"message": "后台任务已添加"}


# 3. 异步上下文管理器示例
async def process_data(task_id: int):
    """使用异步上下文管理器处理数据
    
    此函数演示了如何使用async with来处理特定区域中的异常
    """
    print(f"开始处理任务 {task_id}")
    
    # 使用异步上下文管理器处理异常
    async with background_task_context(
        task_name=f"process_data_{task_id}",
        error_code=CommonErrorCode.INVALID_PARAMS
    ):
        # 模拟数据处理
        items = [{"id": i, "value": random.random()} for i in range(5)]
        result = await process_items(items)
        print(f"处理结果: {result}")
    
    print(f"任务 {task_id} 处理完成")


# 4. 装饰器示例
@background_task_handler(error_code=CommonErrorCode.RESOURCE_EXPIRED)
async def scheduled_cleanup():
    """使用装饰器处理定时清理任务中的异常
    
    此函数演示了如何使用装饰器简化异常处理
    """
    print("开始执行定时清理任务")
    await asyncio.sleep(1.0)
    
    # 随机模拟错误
    if random.random() < 0.4:
        raise ValueError("清理过程中发生错误")
    
    print("清理任务完成")


@app.get("/tasks/cleanup")
async def trigger_cleanup():
    """触发清理任务
    
    此路由演示了带有装饰器的异步函数如何处理异常
    """
    try:
        await scheduled_cleanup()
        return {"message": "清理任务完成"}
    except Exception:
        return {"message": "清理任务失败，但异常已被处理"}


# 添加一个定时任务演示点
@app.on_event("startup")
async def startup_event():
    """应用启动时设置定时任务
    
    此函数演示了如何在应用启动时设置带有异常处理的定时任务
    """
    # 模拟异步任务调度器
    asyncio.create_task(run_scheduled_tasks())


async def run_scheduled_tasks():
    """运行定时任务
    
    此函数模拟了定时任务的运行，包含异常处理
    """
    while True:
        try:
            # 执行定时任务
            await AsyncTaskExceptionMiddleware.execute_task(
                scheduled_cleanup,
                task_name="daily_cleanup",
                error_code=CommonErrorCode.RESOURCE_EXPIRED
            )
        except Exception:
            print("定时任务异常已被处理")
        
        # 等待下一次执行
        await asyncio.sleep(30)  # 实际应用中可能是更长的间隔


# 自定义异常数据模型
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict = {}


# 5. 依赖注入中的异常处理
async def get_current_item(item_id: int):
    """依赖函数：获取当前项目
    
    此函数演示了在依赖注入中使用异步异常处理
    """
    if item_id <= 0:
        raise DomainException(
            code=CommonErrorCode.INVALID_PARAMS,
            details={"item_id": item_id, "reason": "ID必须为正数"}
        )
    
    # 模拟数据库查询
    await asyncio.sleep(0.2)
    
    if item_id > 100:
        raise DomainException(
            code=CommonErrorCode.RESOURCE_NOT_FOUND,
            details={"item_id": item_id}
        )
    
    return {"id": item_id, "name": f"Item {item_id}"}


@app.get(
    "/items/{item_id}",
    responses={
        **common_error_response,
        200: {"model": dict, "description": "成功获取项目"}
    }
)
async def get_item(item: dict = Depends(get_current_item)):
    """获取项目
    
    此路由演示了依赖注入中的异常处理
    """
    return item


if __name__ == "__main__":
    import uvicorn

    # 使用uvicorn运行FastAPI应用
    uvicorn.run(
        "idp.framework.exception.demo.async_demo:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 