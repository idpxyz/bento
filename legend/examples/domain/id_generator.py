"""ID生成器接口"""
from abc import ABC, abstractmethod


class IdGenerator(ABC):
    """ID生成器接口"""

    @abstractmethod
    def generate(self) -> str:
        """生成ID

        Returns:
            str: 生成的ID
        """
        pass
