"""基础映射示例。

本示例展示了如何使用映射器系统进行基础的对象映射，包括：
1. 创建简单的源对象和目标对象类
2. 使用MapperBuilder构建映射器
3. 执行对象映射
4. 处理可能的异常
"""

from dataclasses import dataclass, field
from typing import Optional

from idp.framework.infrastructure.mapper import MapperBuilder


# 源对象类
@dataclass
class UserEntity:
    """用户实体类（源对象）"""
    id: str = ""
    username: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    age: int = 0  # 使用默认值0而不是None，避免类型转换问题


# 目标对象类
@dataclass
class UserDTO:
    """用户DTO类（目标对象）"""
    id: str = ""
    username: str = ""
    email: str = ""
    full_name: str = ""  # 注意这里与源对象的字段名不同
    active: bool = True  # 注意这里与源对象的字段名不同
    age: int = 0  # 使用默认值0而不是None，避免类型转换问题


def basic_mapping_example():
    """
    基本映射示例

    演示如何使用映射器进行基本的对象映射
    """
    try:
        # 创建源对象
        user_entity = UserEntity(
            id="1",
            username="johndoe",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            is_active=True,
            age=30
        )

        print("\n基本映射示例:")
        print(f"源对象: {user_entity}")

        # 手动映射示例
        user_dto = UserDTO(
            id=user_entity.id,
            username=user_entity.username,
            email=user_entity.email,
            full_name=f"{user_entity.first_name} {user_entity.last_name}",
            active=user_entity.is_active,
            age=user_entity.age
        )

        print(f"目标对象 (手动映射): {user_dto}")

        # 演示反向映射
        user_entity_reverse = UserEntity(
            id=user_dto.id,
            username=user_dto.username,
            email=user_dto.email,
            first_name=user_dto.full_name.split(
            )[0] if user_dto.full_name else "",
            last_name=user_dto.full_name.split()[1] if user_dto.full_name and len(
                user_dto.full_name.split()) > 1 else "",
            is_active=user_dto.active,
            age=user_dto.age
        )

        print(f"反向映射结果: {user_entity_reverse}")
        print("注意: 通过手动映射，我们可以正确处理full_name到first_name和last_name的转换")

        # 演示使用MapperBuilder（仅作为示例，不执行）
        print("\n使用MapperBuilder的配置示例（不执行）:")
        print("""
        mapper_builder = MapperBuilder.for_types(UserEntity, UserDTO)
        mapper = mapper_builder.map("id", "id")
            .map("username", "username")
            .map("email", "email")
            .map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}")
            .map("is_active", "active")
            .map("age", "age")
            .build()
        
        user_dto = mapper.map(user_entity)
        """)

        # 实际使用MapperBuilder
        mapper_builder = MapperBuilder.for_types(UserEntity, UserDTO)
        mapper = mapper_builder \
            .map("id", "id") \
            .map("username", "username") \
            .map("email", "email") \
            .map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}") \
            .map("is_active", "active") \
            .map("age", "age") \
            .build()

        # 执行映射
        # 创建目标对象并初始化所有字段
        target_dto = UserDTO()

        # 使用map_to_target而不是map，以确保正确处理类型
        mapper.map_to_target(user_entity, target_dto)

        print(f"目标对象 (使用映射器): {target_dto}")

        # 验证映射结果
        assert target_dto.id == user_entity.id
        assert target_dto.username == user_entity.username
        assert target_dto.email == user_entity.email
        assert target_dto.full_name == f"{user_entity.first_name} {user_entity.last_name}"
        assert target_dto.active == user_entity.is_active
        assert target_dto.age == user_entity.age

        print("映射验证通过!")

    except Exception as e:
        print(f"基本映射示例异常: {e}")
        raise


if __name__ == "__main__":
    basic_mapping_example()
