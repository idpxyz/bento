from http import HTTPStatus

from idp.framework.exception.metadata import ExceptionContext

# 通用响应描述
common_error_response = {
    HTTPStatus.BAD_REQUEST.value: {
        "model": ExceptionContext,
        "description": "请求参数错误"
    },
    HTTPStatus.UNAUTHORIZED.value: {
        "model": ExceptionContext,
        "description": "未授权访问"
    },
    HTTPStatus.FORBIDDEN.value: {
        "model": ExceptionContext,
        "description": "无权限操作"
    },
    HTTPStatus.NOT_FOUND.value: {
        "model": ExceptionContext,
        "description": "资源未找到"
    },
    HTTPStatus.INTERNAL_SERVER_ERROR.value: {
        "model": ExceptionContext,
        "description": "服务器内部错误"
    },
}
