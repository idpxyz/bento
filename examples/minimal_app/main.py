from runtime.bootstrap import create_app
from fastapi import FastAPI
from persistence.sqlalchemy.base import init_async_db, Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from persistence.sqlalchemy.base import _engine  # type: ignore

app: FastAPI = create_app()

@app.on_event("startup")
async def on_startup():
    init_async_db("sqlite+aiosqlite:///./dev.db")
    # create tables lazily
    async with _engine.begin() as conn:  # type: ignore
        await conn.run_sync(Base.metadata.create_all)

@app.get("/healthz")
async def healthz():
    return {"ok": True}
