# 全局配置
from pydantic_settings import BaseSettings


class IDPAppSettings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./db.sqlite"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

app_settings = IDPAppSettings()

# ✅ 配套用法提示
# 初始化实例：settings = AppSettings()
# 在 handler 或服务中调用：settings.ENV
# 在测试中替换：settings = AppSettings(ENV="test")

class ExceptionSettings(BaseSettings):
    EXCEPTION_DEBUG_MODE: bool = True
    
    EXCEPTION_SENTRY_ENABLED: bool = True
    EXCEPTION_ENVIRONMENT: str = "dev"
    EXCEPTION_PROJECT: str = "idp-framework"
    EXCEPTION_DEFAULT_LEVEL: str = "error"
    EXCEPTION_SAMPLE_RATE: float = 1.0
    EXCEPTION_INCLUDE_CAUSE: bool = True
    EXCEPTION_EXPOSE_MESSAGE: bool = True # ✅ 控制是否暴露 message 到客户端

    # ✅ 独立采样率配置
    EXCEPTION_SAMPLE_RATE_DOMAIN: float = 1.0
    EXCEPTION_SAMPLE_RATE_APPLICATION: float = 1.0
    EXCEPTION_SAMPLE_RATE_INFRASTRUCTURE: float = 1.0
    EXCEPTION_SAMPLE_RATE_INTERFACE: float = 1.0

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

exception_settings = ExceptionSettings()

# ✅ 配套用法提示
# 初始化实例：sentry_settings = ExceptionSettings()
# 在 handler 或服务中调用：sentry_settings.enabled
# 在测试中替换：sentry_settings = ExceptionSettings(enabled=False)


