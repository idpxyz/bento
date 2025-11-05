from enum import Enum
from typing import Dict, Literal

from pydantic import BaseModel


class HealthStatus(str, Enum):
    OK = "ok"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    status: Literal[True, False]
    detail: str


class HealthCheckResponse(BaseModel):
    status: HealthStatus
    components: Dict[str, ComponentHealth]
