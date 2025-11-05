from fastapi import APIRouter

from idp.framework.api.health.checker import health_probes
from idp.framework.api.health.schema import (
    ComponentHealth,
    HealthCheckResponse,
    HealthStatus,
)

router = APIRouter()


@router.get("/healthz", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    results = {}

    for name, probe in health_probes.items():
        ok, detail = await probe()
        results[name] = ComponentHealth(status=ok, detail=detail)

    status = HealthStatus.OK if all(v.status for v in results.values()) else HealthStatus.UNHEALTHY

    return HealthCheckResponse(status=status, components=results)
