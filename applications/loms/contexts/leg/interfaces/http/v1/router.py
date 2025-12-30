from fastapi import APIRouter, Header, Request
from loms.shared.platform.i18n.catalog import CATALOG, t
from pydantic import BaseModel, Field

router = APIRouter()


class OkResponse(BaseModel):
    code: str = Field(default="OK")
    message: str


class I18nTestResponse(BaseModel):
    locale: str
    messages: dict[str, str]


@router.get("/_bc/leg/ping", response_model=OkResponse)
async def ping(
    request: Request,
    accept_language: str = Header(default="en-US", alias="Accept-Language"),
):
    locale = getattr(request.state, "locale", None) or accept_language.split(",")[0]
    return OkResponse(message=t(locale, "OK"))


@router.get("/_bc/leg/i18n-test", response_model=I18nTestResponse)
async def i18n_test(
    accept_language: str = Header(default="en-US", alias="Accept-Language"),
):
    """
    测试多语言功能。

    使用 Accept-Language header 切换语言：
    - zh-CN: 中文
    - en-US: 英文

    示例：
    curl -H "Accept-Language: zh-CN" http://localhost:8002/api/v1/_bc/leg/i18n-test
    """
    locale = accept_language.split(",")[0]

    # 获取几个示例 reason codes 的翻译
    test_codes = [
        "VALIDATION_FAILED",
        "STATE_CONFLICT",
        "RESOURCE_NOT_FOUND",
        "IDEMPOTENCY_KEY_MISMATCH",
    ]

    messages = {code: t(locale, code) for code in test_codes}

    return I18nTestResponse(locale=locale, messages=messages)


@router.get("/_bc/leg/i18n-locales")
async def list_locales():
    """列出所有支持的语言"""
    return {"supported_locales": list(CATALOG.keys())}
