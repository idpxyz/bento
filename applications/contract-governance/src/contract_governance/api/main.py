from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contract_governance.api.router import router
from contract_governance.config.settings import Settings

settings = Settings()

app = FastAPI(
    title=settings.app_name,
    description="Enterprise-grade Contract Governance Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
