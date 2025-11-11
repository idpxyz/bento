from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from idp.projects.godata.master_data.application.services.tiangan_service import (
    TianganService,
)
from idp.projects.godata.master_data.domain.aggregate.tiangan import Tiangan
from idp.projects.godata.master_data.domain.value_objects.tiangan_combination import (
    TianganCombination,
)


# Pydantic模型用于API请求和响应
class TianganCreateRequest(BaseModel):
    """创建天干请求模型"""
    name: str
    order: int
    yin_yang: str
    wu_xing: str
    na_yin: str
    description: str

    # 新增属性
    direction: Optional[str] = None  # 方位
    season: Optional[str] = None  # 季节
    color: Optional[str] = None  # 颜色
    taste: Optional[str] = None  # 五味
    emotion: Optional[str] = None  # 情志
    organ: Optional[str] = None  # 脏腑
    body_part: Optional[str] = None  # 身体部位
    sound: Optional[str] = None  # 五音
    he_luo_number: Optional[int] = None  # 河洛配数


class TianganResponse(BaseModel):
    """天干响应模型"""
    id: str
    name: str
    order: int
    yin_yang: str
    wu_xing: str
    na_yin: str
    description: str
    he_hua: Optional[str] = None

    # 新增属性
    direction: Optional[str] = None  # 方位
    season: Optional[str] = None  # 季节
    color: Optional[str] = None  # 颜色
    taste: Optional[str] = None  # 五味
    emotion: Optional[str] = None  # 情志
    organ: Optional[str] = None  # 脏腑
    body_part: Optional[str] = None  # 身体部位
    sound: Optional[str] = None  # 五音
    he_luo_number: Optional[int] = None  # 河洛配数

    class Config:
        from_attributes = True


class CombinationRequest(BaseModel):
    """天干组合请求模型"""
    tiangan1: str
    tiangan2: str


class CombinationResponse(BaseModel):
    """天干组合响应模型"""
    first_tiangan: str
    second_tiangan: str
    he_hua_result: str
    description: str
    is_valid: bool

# 依赖注入函数


def get_tiangan_service() -> TianganService:
    """获取天干服务实例 - 这里应该从依赖注入容器获取"""
    # 实际实现中，这里应该从DI容器获取仓储实现
    from idp.projects.godata.master_data.infrastructure.repositories.memory_tiangan_repository import (
        MemoryTianganRepository,
    )
    repository = MemoryTianganRepository()
    return TianganService(repository)


# 创建路由器
router = APIRouter(prefix="/tiangan", tags=["天干"])


@router.get("/", response_model=List[TianganResponse])
async def get_all_tiangans(
    service: TianganService = Depends(get_tiangan_service)
):
    """获取所有天干"""
    tiangans = await service.get_all_tiangans()
    return [TianganResponse.from_orm(tiangan) for tiangan in tiangans]


@router.get("/{name}", response_model=TianganResponse)
async def get_tiangan_by_name(
    name: str,
    service: TianganService = Depends(get_tiangan_service)
):
    """根据名称获取天干"""
    tiangan = await service.get_tiangan_by_name(name)
    if not tiangan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"天干 '{name}' 不存在"
        )
    return TianganResponse.from_orm(tiangan)


@router.get("/order/{order}", response_model=TianganResponse)
async def get_tiangan_by_order(
    order: int,
    service: TianganService = Depends(get_tiangan_service)
):
    """根据序号获取天干"""
    tiangan = await service.get_tiangan_by_order(order)
    if not tiangan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"序号为 {order} 的天干不存在"
        )
    return TianganResponse.from_orm(tiangan)


@router.get("/wuxing/{wu_xing}", response_model=List[TianganResponse])
async def get_tiangans_by_wuxing(
    wu_xing: str,
    service: TianganService = Depends(get_tiangan_service)
):
    """根据五行属性获取天干列表"""
    tiangans = await service.get_tiangans_by_wuxing(wu_xing)
    return [TianganResponse.from_orm(tiangan) for tiangan in tiangans]


@router.get("/yin-yang/{yin_yang}", response_model=List[TianganResponse])
async def get_tiangans_by_yin_yang(
    yin_yang: str,
    service: TianganService = Depends(get_tiangan_service)
):
    """根据阴阳属性获取天干列表"""
    if yin_yang == "阳":
        tiangans = await service.get_yang_tiangans()
    elif yin_yang == "阴":
        tiangans = await service.get_yin_tiangans()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="阴阳属性必须是 '阳' 或 '阴'"
        )
    return [TianganResponse.from_orm(tiangan) for tiangan in tiangans]


@router.post("/", response_model=TianganResponse, status_code=status.HTTP_201_CREATED)
async def create_tiangan(
    request: TianganCreateRequest,
    service: TianganService = Depends(get_tiangan_service)
):
    """创建新的天干"""
    try:
        tiangan = await service.create_tiangan(
            name=request.name,
            order=request.order,
            yin_yang=request.yin_yang,
            wu_xing=request.wu_xing,
            na_yin=request.na_yin,
            description=request.description,
            direction=request.direction,
            season=request.season,
            color=request.color,
            taste=request.taste,
            emotion=request.emotion,
            organ=request.organ,
            body_part=request.body_part,
            sound=request.sound,
            he_luo_number=request.he_luo_number
        )
        return TianganResponse.from_orm(tiangan)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/combination", response_model=CombinationResponse)
async def check_tiangan_combination(
    request: CombinationRequest,
    service: TianganService = Depends(get_tiangan_service)
):
    """检查两个天干是否可以合化"""
    combination = await service.check_combination(
        request.tiangan1,
        request.tiangan2
    )

    if combination:
        return CombinationResponse(
            first_tiangan=combination.first_tiangan,
            second_tiangan=combination.second_tiangan,
            he_hua_result=combination.he_hua_result.value,
            description=combination.get_description(),
            is_valid=True
        )
    else:
        return CombinationResponse(
            first_tiangan=request.tiangan1,
            second_tiangan=request.tiangan2,
            he_hua_result="",
            description=f"{request.tiangan1} 和 {request.tiangan2} 不能合化",
            is_valid=False
        )


@router.get("/{name}/compatible", response_model=List[TianganResponse])
async def get_compatible_tiangans(
    name: str,
    service: TianganService = Depends(get_tiangan_service)
):
    """获取与指定天干相合的天干列表"""
    compatible = await service.get_compatible_tiangans(name)
    return [TianganResponse.from_orm(tiangan) for tiangan in compatible]


@router.get("/{name}/next/{steps}", response_model=TianganResponse)
async def get_next_tiangan(
    name: str,
    steps: int = 1,
    service: TianganService = Depends(get_tiangan_service)
):
    """获取指定步数后的天干"""
    next_tiangan = await service.get_next_tiangan_cycle(name, steps)
    if not next_tiangan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"天干 '{name}' 不存在"
        )
    return TianganResponse.from_orm(next_tiangan)
