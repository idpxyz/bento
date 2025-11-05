"""命令处理器基类

定义命令处理器的基类。
"""
from typing import Generic, TypeVar

from idp.framework.application.command.command import BaseCommand

CommandType = TypeVar('CommandType', bound=BaseCommand)
ResultType = TypeVar('ResultType')


class BaseCommandHandler(Generic[CommandType, ResultType]):
    """命令处理器基类

    泛型参数:
        CommandType: 命令类型
        ResultType: 处理结果类型
    """

    async def handle(self, command: CommandType) -> ResultType:
        """处理命令

        Args:
            command: 要处理的命令

        Returns:
            ResultType: 处理结果
        """
        raise NotImplementedError
