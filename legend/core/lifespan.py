# lifespan 或 startup/shutdown 钩子定义

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 应用启动中...")
    yield
    print("🛑 应用关闭中...")
