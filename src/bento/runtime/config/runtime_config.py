"""Runtime configuration with validation.

Provides RuntimeConfig dataclass with comprehensive validation
for all configuration parameters.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from bento.infrastructure.database.config import DatabaseConfig

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConfig:
    """Configuration for BentoRuntime with validation.

    Validates all configuration parameters to catch errors early.
    """

    contracts_path: str | None = None
    require_contracts: bool = False
    environment: str = "local"
    service_name: str = "bento-app"
    skip_gates_in_local: bool = True
    database: "DatabaseConfig | None" = None
    test_mode: bool = False

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_service_name()
        self._validate_environment()
        self._validate_contracts_path()

    def _validate_service_name(self) -> None:
        """Validate service name format."""
        if not self.service_name:
            raise ValueError("service_name cannot be empty")

        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if not all(c in valid_chars for c in self.service_name):
            raise ValueError(
                f"Invalid service name: {self.service_name}. "
                f"Only alphanumeric characters, underscores, and hyphens are allowed."
            )

    def _validate_environment(self) -> None:
        """Validate environment value."""
        valid_envs = ("local", "dev", "stage", "prod")
        if self.environment not in valid_envs:
            raise ValueError(
                f"Invalid environment: {self.environment}. Must be one of {valid_envs}."
            )

    def _validate_contracts_path(self) -> None:
        """Validate contracts path if provided."""
        if self.contracts_path:
            path = Path(self.contracts_path)
            if not path.is_absolute():
                logger.warning(
                    f"contracts_path is relative: {self.contracts_path}. "
                    f"Consider using absolute paths for clarity."
                )
