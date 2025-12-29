from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Contract Governance"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite:///./contract_governance.db"
    database_echo: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8001

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
