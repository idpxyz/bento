from pydantic import BaseSettings

from idp.framework.infrastructure.config_bak import config


class ExceptionConfig(BaseSettings):
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


exception_settings = ExceptionConfig(
    EXCEPTION_DEBUG_MODE=config.get("exception", "debug_mode", True), # ✅ 控制是否启用调试模式
    EXCEPTION_SENTRY_ENABLED=config.get("exception", "sentry.enabled", True), # ✅ 控制是否启用 Sentry
    EXCEPTION_SENTRY_DSN=config.get("exception", "sentry.dsn", ""), # ✅ 控制 Sentry DSN
    EXCEPTION_SEND_DEFAULT_PII=config.get("exception", "sentry.send_default_pii", True), # ✅ 控制是否发送默认的 PII 数据
    EXCEPTION_ENVIRONMENT=config.get("exception", "sentry.environment", "dev"), # ✅ 控制 Sentry 环境
    EXCEPTION_PROJECT=config.get("exception", "sentry.project", "idp-framework"), # ✅ 控制 Sentry 项目
    EXCEPTION_DEFAULT_LEVEL=config.get("exception", "sentry.default_level", "error"), # ✅ 控制 Sentry 默认级别
    EXCEPTION_SAMPLE_RATE=config.get("exception", "sentry.sample_rate", 1.0), # ✅ 控制 Sentry 采样率
    EXCEPTION_INCLUDE_CAUSE=config.get("exception", "sentry.include_cause", True), # ✅ 控制是否包含异常原因
    EXCEPTION_EXPOSE_MESSAGE=config.get("exception", "sentry.expose_message", True), # ✅ 控制是否暴露 message 到客户端
    EXCEPTION_SAMPLE_RATE_DOMAIN=config.get("exception", "sentry.sample_rate_domain", 1.0), # ✅ 控制域级采样率
    EXCEPTION_SAMPLE_RATE_APPLICATION=config.get("exception", "sentry.sample_rate_application", 1.0), # ✅ 控制应用级采样率
    EXCEPTION_SAMPLE_RATE_INFRASTRUCTURE=config.get("exception", "sentry.sample_rate_infrastructure", 1.0), # ✅ 控制基础设施级采样率
    EXCEPTION_SAMPLE_RATE_INTERFACE=config.get("exception", "sentry.sample_rate_interface", 1.0), # ✅ 控制接口级采样率
)
