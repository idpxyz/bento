from fastapi import Request
from fastapi.responses import JSONResponse
from loms.shared.platform.errors.exceptions import AppError


def _best_locale(request: Request) -> str | None:
    header = request.headers.get("accept-language")
    return header.split(",")[0].strip() if header else None

def install_error_handlers(app, error_mapper):
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError):
        status, body, headers = error_mapper.to_http(exc, locale=_best_locale(request))
        return JSONResponse(status_code=status, content=body.model_dump(), headers=headers)
