class MessageDomainException(Exception):
    """消息领域异常基类"""
    pass


class InvalidMessageStateException(MessageDomainException):
    """无效的消息状态异常"""
    pass


class InvalidEventTypeException(MessageDomainException):
    """无效的事件类型异常"""
    pass


class InvalidPayloadException(MessageDomainException):
    """无效的消息负载异常"""
    pass 