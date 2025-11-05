# 提供 DI 的 Depends 依赖函数，如获取当前用户、当前租户

from fastapi import Depends, HTTPException

from idp.framework.core.security import decode_token
from idp.framework.exceptions.http_exceptions import UnauthorizedException


async def get_current_user(token: str = Depends(...)):
    user = decode_token(token)
    if not user:
        raise UnauthorizedException()
    return user
