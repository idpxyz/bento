import asyncio
import importlib
from typing import List

# Ensure codecs are registered before creating the event bus
import idp.framework.infrastructure.messaging.codec
from idp.framework.infrastructure.messaging.codec.json_codec import JsonMessageCodec
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import register_codec
from idp.framework.infrastructure.messaging.dispatcher.subscriber_runner import (
    run_event_subscribers,
)
from idp.framework.infrastructure.messaging.pulsar.event_bus import PulsarEventBus

# Ensure JSON codec is registered explicitly
try:
    register_codec("json", JsonMessageCodec())
except Exception as e:
    print(f"Warning: JsonMessageCodec registration error: {e}")

event_bus = PulsarEventBus()

def load_handlers():
    # 注意：根据你项目结构调整路径
    importlib.import_module("idp.framework.api.messaging.handlers.user_handlers")
    # importlib.import_module("app.handlers.xxx") # 可扩展导入更多

    # lifespan中调用
    # @app.on_event("startup")
    # async def startup_event():
    # load_all_event_handlers()
    # asyncio.create_task(start_subscribers())

def register_messaging_handlers():
    async def on_something(event: MessageEnvelope):
        print(f"处理事件 {event.event_type}, 内容: {event.payload}")

    event_bus.register_handler("test.topic", on_something)

async def start_subscribers():
    await run_event_subscribers([
        "persistent://public/default/test.topic"
    ])
