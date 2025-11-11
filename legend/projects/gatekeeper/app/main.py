# app/main.py
import uvicorn
from app.routes import audit, policy, webhook_logto
from fastapi import FastAPI

app = FastAPI(title="Gatekeeper")
app.include_router(policy.router, prefix="/policy", tags=["policy"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
app.include_router(webhook_logto.router, prefix="/webhook", tags=["webhook"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
