from fastapi import APIRouter, Request
from loms.shared.platform.i18n.i18n import t
from pydantic import BaseModel, Field

router = APIRouter()


class OkResponse(BaseModel):
    code: str = Field(default="OK")
    message: str


@router.get("/_bc/logistics_product/ping", response_model=OkResponse)
async def ping(request: Request):
    locale = request.state.locale
    return OkResponse(message=t(locale, "OK"))
