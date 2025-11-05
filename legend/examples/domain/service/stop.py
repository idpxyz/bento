"""站点相关的领域服务"""
from typing import List, Optional

from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.vo.location import Location


class StopDomainService:
    """站点领域服务"""

    @staticmethod
    def calculate_distance(location1: Location, location2: Location) -> float:
        """计算两个位置之间的距离（公里）

        Args:
            location1: 位置1
            location2: 位置2

        Returns:
            float: 距离（公里）
        """
        # 使用Haversine公式计算球面距离
        from math import atan2, cos, radians, sin, sqrt

        R = 6371  # 地球半径（公里）

        lat1, lon1 = radians(location1.latitude), radians(location1.longitude)
        lat2, lon2 = radians(location2.latitude), radians(location2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c

        return round(distance, 2)

    @staticmethod
    def find_nearest_stop(target_location: Location, stops: List[Stop]) -> Optional[Stop]:
        """查找最近的站点

        Args:
            target_location: 目标位置
            stops: 站点列表

        Returns:
            Optional[Stop]: 最近的站点，如果没有站点则返回None
        """
        if not stops:
            return None

        nearest_stop = min(
            stops,
            key=lambda stop: StopDomainService.calculate_distance(
                target_location,
                stop.location
            )
        )

        return nearest_stop

    @staticmethod
    def validate_stop_sequence(stops: List[Stop]) -> bool:
        """验证站点序列的合理性

        Args:
            stops: 站点列表

        Returns:
            bool: 是否合理
        """
        if not stops:
            return False

        # 检查站点是否都处于活动状态
        if not all(stop.is_active for stop in stops):
            return False

        # 检查相邻站点之间的距离是否合理（例如不超过100公里）
        for i in range(len(stops) - 1):
            distance = StopDomainService.calculate_distance(
                stops[i].location,
                stops[i + 1].location
            )
            if distance > 100:  # 假设最大合理距离为100公里
                return False

        return True
