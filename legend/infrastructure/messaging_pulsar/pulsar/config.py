import os
from functools import lru_cache

import pulsar


class PulsarSettings:
    """
    Pulsar 配置封装，可从环境变量或 .env 文件中读取。
    """

    def __init__(self):
        self.service_url = os.getenv("PULSAR_URL", "pulsar://192.168.8.137:6650")
        self.auth_token = os.getenv("PULSAR_AUTH_TOKEN", None)
        self.tls_trust_cert_path = os.getenv("PULSAR_TLS_CERT_PATH", None)
        self.tls_enabled = os.getenv("PULSAR_TLS_ENABLED", "false").lower() == "true"

    def get_client(self) -> pulsar.Client:
        """
        初始化 Pulsar 客户端，支持 TLS 和 Token 认证。
        """
        kwargs = {
            "service_url": self.service_url,
        }

        if self.tls_enabled:
            kwargs["tls_trust_certs_file_path"] = self.tls_trust_cert_path
            kwargs["tls_validate_hostname"] = True
            kwargs["use_tls"] = True

        if self.auth_token:
            kwargs["authentication"] = pulsar.AuthenticationToken(self.auth_token)

        return pulsar.Client(**kwargs)


@lru_cache()
def get_pulsar_settings() -> PulsarSettings:
    """
    返回全局单例配置对象
    """
    return PulsarSettings()


@lru_cache()
def get_pulsar_client() -> pulsar.Client:
    """
    返回全局单例 Pulsar 客户端
    """
    return get_pulsar_settings().get_client()
