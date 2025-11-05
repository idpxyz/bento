"""位置值对象"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Location:
    """位置值对象

    表示一个地理位置，包含纬度和经度。
    值对象是不可变的，一旦创建就不能修改。
    """
    latitude: float
    longitude: float

    def __post_init__(self):
        """初始化后验证数据"""
        if not -90 <= self.latitude <= 90:
            raise ValueError("Invalid latitude value")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Invalid longitude value")

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Location']:
        """从字典创建位置值对象

        Args:
            data: 包含 latitude 和 longitude 的字典

        Returns:
            Optional[Location]: 位置值对象，如果数据无效则返回 None
        """
        try:
            return cls(
                latitude=float(data.get('latitude', 0)),
                longitude=float(data.get('longitude', 0))
            )
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            dict: 包含 latitude 和 longitude 的字典
        """
        return {
            'latitude': self.latitude,
            'longitude': self.longitude
        }
