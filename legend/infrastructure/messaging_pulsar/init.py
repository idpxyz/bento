import asyncio
import importlib
import os
import pkgutil
import sys

from infrastructure.messaging.codec import protobuf

from idp.framework.infrastructure.messaging.dispatcher.subscriber_runner import (
    run_event_subscribers,
)


def auto_register_codecs():
    """注册所有消息编解码器"""
    try:
        # 确保不会导入已存在的模块
        if 'idp.framework.infrastructure.messaging.codec.json' in sys.modules:
            del sys.modules['idp.framework.infrastructure.messaging.codec.json']
            
        # 直接导入具体的编解码器模块确保它们被注册
        # 使用 importlib 动态导入避免命名冲突
        json_module = importlib.import_module('idp.framework.infrastructure.messaging.codec.json')
        avro_module = importlib.import_module('idp.framework.infrastructure.messaging.codec.avro')
        
        print("[codecs] JSON, Protocol Buffers, Avro 编解码器已注册")
    except ImportError as e:
        print(f"[warning] 编解码器导入失败: {e}")
        # 回退到通用导入
        import idp.framework.infrastructure.messaging.codec  # 会触发 __init__.py 自动扫描
        print("[codecs] 已通过模块扫描注册编解码器")


def auto_register_handlers():
    """注册所有事件处理器"""
    try:
        base_package = "app.handlers"
        base_path = os.path.join(os.path.dirname(__file__), "../../../app/handlers")
        if os.path.exists(base_path):
            for _, module_name, is_pkg in pkgutil.iter_modules([base_path]):
                if not is_pkg:
                    importlib.import_module(f"{base_package}.{module_name}")
            print(f"[handlers] 已从 {base_path} 注册事件处理器")
        else:
            print(f"[warning] 未找到处理器目录: {base_path}")
    except Exception as e:
        print(f"[error] 注册事件处理器失败: {e}")


def register_observer_hook():
    """注册可观测性钩子"""
    try:
        from idp.framework.infrastructure.messaging.observability.hook import (
            set_observer,
        )
    
        def simple_logger(event_type, correlation_id, success, duration, error):
            print(f"[obs] {event_type} trace={correlation_id} success={success} time={duration:.2f}s error={error}")
    
        set_observer(simple_logger)
        print("[obs] 已注册默认观察器")
    except Exception as e:
        print(f"[error] 注册观察器失败: {e}")


async def init_messaging():
    """初始化消息系统"""
    print("\n[init] 开始初始化消息系统")
    
    print("[init] 注册消息编解码器")
    auto_register_codecs()

    print("[init] 注册事件处理器")
    auto_register_handlers()

    print("[init] 注册可观测性钩子")
    register_observer_hook()

    print("[init] 启动订阅监听器")
    await run_event_subscribers([
        "persistent://public/default/user.registered"
    ])
    
    print("[init] 消息系统初始化完成\n")


async def shutdown_messaging():
    """关闭消息系统"""
    print("[shutdown] 正在关闭消息系统...")
    # 这里添加清理代码，如关闭连接等
    print("[shutdown] 消息系统已关闭")

# ✅ 在 FastAPI 启动时调用

# from fastapi import FastAPI
# from contextlib import asynccontextmanager
# from idp.framework.infrastructure.messaging.init import init_messaging, shutdown_messaging
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await init_messaging()
#     yield
#     await shutdown_messaging()
#
# app = FastAPI(lifespan=lifespan)
