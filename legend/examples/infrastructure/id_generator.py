"""ID生成器实现"""
import uuid

from idp.framework.examples.domain.id_generator import IdGenerator


class UuidIdGenerator(IdGenerator):
    """基于UUID的ID生成器"""

    def generate(self) -> str:
        """生成UUID

        Returns:
            str: 生成的UUID
        """
        return str(uuid.uuid4())
