from http import HTTPStatus

from idp.framework.exception.code import ErrorCode


class OrderErrorCode(ErrorCode):
    ORDER_NOT_FOUND = ErrorCode("100201", "订单未找到", HTTPStatus.NOT_FOUND)

    ORDER_ALREADY_EXISTS = ErrorCode("100202", "订单已存在", HTTPStatus.CONFLICT)

    ORDER_INVALID_STATUS = ErrorCode("100203", "订单状态无效", HTTPStatus.BAD_REQUEST)
