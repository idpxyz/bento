"""站点相关的请求和响应模型"""
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.vo.contact import Contact
from idp.framework.examples.domain.vo.location import Location


class LocationSchema(BaseModel):
    """位置模型"""
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")

    def to_vo(self) -> Location:
        """转换为值对象

        Returns:
            Location: 位置值对象
        """
        return Location(self.latitude, self.longitude)


class ContactSchema(BaseModel):
    """联系人模型"""
    name: str = Field(..., min_length=1, max_length=50, description="联系人姓名")
    phone: str = Field(..., min_length=1, max_length=20, description="联系人电话")
    email: EmailStr = Field(..., description="联系人邮箱")

    def to_vo(self) -> Contact:
        """转换为值对象

        Returns:
            Contact: 联系人值对象
        """
        return Contact(self.name, self.phone, self.email)


class StopResponse(BaseModel):
    """站点响应模型"""
    id: str = Field(..., description="站点ID")
    name: str = Field(..., description="站点名称")
    address: str = Field(..., description="站点地址")
    location: Optional[LocationSchema] = Field(None, description="站点位置")
    contact: Optional[ContactSchema] = Field(None, description="站点联系人")
    description: Optional[str] = Field(None, description="站点描述")
    is_active: bool = Field(..., description="是否启用")
    tenant_id: str = Field(..., description="租户ID")

    @classmethod
    def from_domain(cls, stop: Stop) -> 'StopResponse':
        """从领域对象创建响应模型

        Args:
            stop: 站点领域对象

        Returns:
            StopResponse: 站点响应模型
        """
        return cls(
            id=stop.id,
            name=stop.name,
            address=stop.address,
            location=LocationSchema(
                latitude=stop.location.latitude,
                longitude=stop.location.longitude
            ) if stop.location else None,
            contact=ContactSchema(
                name=stop.contact.name,
                phone=stop.contact.phone,
                email=stop.contact.email
            ) if stop.contact else None,
            description=stop.description,
            is_active=stop.is_active,
            tenant_id=stop.tenant_id
        )


class CreateStopRequest(BaseModel):
    """创建站点请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="站点名称")
    address: str = Field(..., min_length=1, max_length=200, description="站点地址")
    location: Optional[LocationSchema] = Field(None, description="站点位置")
    contact: Optional[ContactSchema] = Field(None, description="站点联系人")
    description: Optional[str] = Field(
        None, max_length=500, description="站点描述")
    is_active: bool = Field(True, description="是否启用")
    tenant_id: str = Field(..., description="租户ID")


class UpdateStopRequest(CreateStopRequest):
    """更新站点请求模型"""
    pass


class UpdateStopLocationRequest(BaseModel):
    """更新站点位置请求模型"""
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")
    tenant_id: str = Field(..., description="租户ID")


class UpdateStopContactRequest(BaseModel):
    """更新站点联系人请求模型"""
    name: str = Field(..., min_length=1, max_length=50, description="联系人姓名")
    phone: str = Field(..., min_length=1, max_length=20, description="联系人电话")
    email: EmailStr = Field(..., description="联系人邮箱")
    tenant_id: str = Field(..., description="租户ID")
