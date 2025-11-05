"""领域事件示例。



提供领域事件的示例实现，展示如何创建和使用领域事件。

"""



from datetime import datetime

from typing import Dict, Any, Optional, List



from idp.framework.domain.event.base import DomainEvent





class UserCreatedEvent(DomainEvent):

    """用户创建事件"""

    

    def __init__(

        self,

        user_id: str,

        username: str,

        email: str,

        roles: List[str] = None,

        aggregate_id: Optional[str] = None,

        event_id: Optional[str] = None,

        timestamp: Optional[datetime] = None,

        version: int = 1,

        metadata: Optional[Dict[str, Any]] = None

    ):

        """初始化用户创建事件

        

        Args:

            user_id: 用户ID

            username: 用户名

            email: 电子邮件

            roles: 角色列表

            aggregate_id: 聚合根ID，默认使用user_id

            event_id: 事件ID

            timestamp: 事件时间戳

            version: 事件版本

            metadata: 事件元数据

        """

        # 如果未提供聚合根ID，则使用用户ID

        if aggregate_id is None:

            aggregate_id = user_id

            

        super().__init__(

            aggregate_id=aggregate_id,

            event_id=event_id,

            timestamp=timestamp,

            version=version,

            metadata=metadata

        )

        

        self._user_id = user_id

        self._username = username

        self._email = email

        self._roles = roles or []

    

    @property

    def user_id(self) -> str:

        """获取用户ID"""

        return self._user_id

    

    @property

    def username(self) -> str:

        """获取用户名"""

        return self._username

    

    @property

    def email(self) -> str:

        """获取电子邮件"""

        return self._email

    

    @property

    def roles(self) -> List[str]:

        """获取角色列表"""

        return self._roles.copy()  # 返回副本以保持不可变性

    

    def get_payload(self) -> Dict[str, Any]:

        """获取事件负载

        

        Returns:

            事件负载的字典表示

        """

        return {

            "user_id": self.user_id,

            "username": self.username,

            "email": self.email,

            "roles": self.roles

        }

    

    @classmethod

    def from_payload(

        cls,

        payload: Dict[str, Any],

        aggregate_id: Optional[str] = None,

        event_id: Optional[str] = None,

        timestamp: Optional[datetime] = None,

        version: int = 1,

        metadata: Optional[Dict[str, Any]] = None

    ) -> 'UserCreatedEvent':

        """从负载创建事件

        

        Args:

            payload: 事件负载

            aggregate_id: 聚合根ID

            event_id: 事件ID

            timestamp: 事件时间戳

            version: 事件版本

            metadata: 事件元数据

            

        Returns:

            创建的事件

        """

        return cls(

            user_id=payload["user_id"],

            username=payload["username"],

            email=payload["email"],

            roles=payload.get("roles", []),

            aggregate_id=aggregate_id,

            event_id=event_id,

            timestamp=timestamp,

            version=version,

            metadata=metadata

        )





class UserUpdatedEvent(DomainEvent):

    """用户更新事件"""

    

    def __init__(

        self,

        user_id: str,

        changes: Dict[str, Any],

        aggregate_id: Optional[str] = None,

        event_id: Optional[str] = None,

        timestamp: Optional[datetime] = None,

        version: int = 1,

        metadata: Optional[Dict[str, Any]] = None

    ):

        """初始化用户更新事件

        

        Args:

            user_id: 用户ID

            changes: 变更字段及其值

            aggregate_id: 聚合根ID，默认使用user_id

            event_id: 事件ID

            timestamp: 事件时间戳

            version: 事件版本

            metadata: 事件元数据

        """

        # 如果未提供聚合根ID，则使用用户ID

        if aggregate_id is None:

            aggregate_id = user_id

            

        super().__init__(

            aggregate_id=aggregate_id,

            event_id=event_id,

            timestamp=timestamp,

            version=version,

            metadata=metadata

        )

        

        self._user_id = user_id

        self._changes = changes

    

    @property

    def user_id(self) -> str:

        """获取用户ID"""

        return self._user_id

    

    @property

    def changes(self) -> Dict[str, Any]:

        """获取变更内容"""

        return self._changes.copy()  # 返回副本以保持不可变性

    

    def get_payload(self) -> Dict[str, Any]:

        """获取事件负载

        

        Returns:

            事件负载的字典表示

        """

        return {

            "user_id": self.user_id,

            "changes": self.changes

        }

    

    @classmethod

    def from_payload(

        cls,

        payload: Dict[str, Any],

        aggregate_id: Optional[str] = None,

        event_id: Optional[str] = None,

        timestamp: Optional[datetime] = None,

        version: int = 1,

        metadata: Optional[Dict[str, Any]] = None

    ) -> 'UserUpdatedEvent':

        """从负载创建事件

        

        Args:

            payload: 事件负载

            aggregate_id: 聚合根ID

            event_id: 事件ID

            timestamp: 事件时间戳

            version: 事件版本

            metadata: 事件元数据

            

        Returns:

            创建的事件

        """

        return cls(

            user_id=payload["user_id"],

            changes=payload["changes"],

            aggregate_id=aggregate_id,

            event_id=event_id,

            timestamp=timestamp,

            version=version,

            metadata=metadata

        )





# 使用示例

def example_usage():

    # 创建用户创建事件

    user_created = UserCreatedEvent(

        user_id="user-123",

        username="john_doe",

        email="john@example.com",

        roles=["user", "admin"],

        metadata={"source": "user_service", "ip_address": "192.168.1.1"}

    )

    

    # 序列化为字典

    event_dict = user_created.to_dict()

    print(f"序列化事件: {event_dict}")

    

    # 添加元数据

    event_with_metadata = user_created.with_metadata("request_id", "req-456")

    print(f"添加元数据后的事件ID: {event_with_metadata.event_id}")

    print(f"添加元数据后的元数据: {event_with_metadata.metadata}")

    

    # 创建用户更新事件

    user_updated = UserUpdatedEvent(

        user_id="user-123",

        changes={"username": "john_smith", "email": "john.smith@example.com"},

        metadata={"source": "profile_service"}

    )

    

    # 获取事件类型

    print(f"事件类型: {user_updated.event_type}")

    

    # 获取事件负载

    print(f"事件负载: {user_updated.get_payload()}")





if __name__ == "__main__":

    example_usage() 