from fastapi import APIRouter

from loms.bc.fulfillment_request.interfaces.http.v1.router import router as fr_router
from loms.bc.shipment.interfaces.http.v1.router import router as shipment_router
from loms.bc.leg.interfaces.http.v1.router import router as leg_router
from loms.bc.orchestration.interfaces.http.v1.router import router as orch_router
from loms.bc.integration.interfaces.http.v1.router import router as integration_router
from loms.bc.document.interfaces.http.v1.router import router as document_router
from loms.bc.tracking.interfaces.http.v1.router import router as tracking_router
from loms.bc.operations_issue.interfaces.http.v1.router import router as issue_router
from loms.bc.rating.interfaces.http.v1.router import router as rating_router
from loms.bc.billing.interfaces.http.v1.router import router as billing_router
from loms.bc.provider.interfaces.http.v1.router import router as provider_router
from loms.bc.network_planning.interfaces.http.v1.router import router as network_router
from loms.bc.logistics_product.interfaces.http.v1.router import router as product_router
from loms.bc.tenant_config.interfaces.http.v1.router import router as tenant_router

def build_v1_router() -> APIRouter:
    r = APIRouter()
    r.include_router(fr_router)
    r.include_router(shipment_router)
    r.include_router(leg_router)
    r.include_router(orch_router)
    r.include_router(integration_router)
    r.include_router(document_router)
    r.include_router(tracking_router)
    r.include_router(issue_router)
    r.include_router(rating_router)
    r.include_router(billing_router)
    r.include_router(provider_router)
    r.include_router(network_router)
    r.include_router(product_router)
    r.include_router(tenant_router)
    return r
