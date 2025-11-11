# infrastructure/settings.py
from pydantic import BaseSettings


class Settings(BaseSettings):
    opa_url: str = "http://localhost:8181"
    database_url: str = "postgresql+asyncpg://user:password@localhost/gatekeeper"
    # 其它配置项...

    class Config:
        env_file = ".env"


settings = Settings()
