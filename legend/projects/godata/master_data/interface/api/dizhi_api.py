from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from idp.projects.godata.master_data.application.services.dizhi_service import (
    DizhiService,
)
from idp.projects.godata.master_data.application.services.tiangan_service import (
    TianganService,
)
from idp.projects.godata.master_data.domain.aggregate.dizhi import Dizhi
from idp.projects.godata.master_data.domain.value_objects.dizhi_combination import (
    DizhiCombination,
    DizhiRelationType,
    SanHeGroup,
)
from idp.projects.godata.master_data.interface.api.tiangan_api import (
    get_tiangan_service,
)


class DizhiCreateRequest(BaseModel):
    """创建地支请求模型"""
    name: str
    order: int
    animal: str
    yin_yang: str
    wu_xing: str
    na_yin: str
    description: str

    # 新增属性
    cang_gan: Optional[List[str]] = None  # 藏干
    direction: Optional[str] = None  # 方位
    time_period: Optional[str] = None  # 时辰
    month: Optional[str] = None  # 月份
    season: Optional[str] = None  # 季节
    color: Optional[str] = None  # 颜色
    taste: Optional[str] = None  # 五味
    emotion: Optional[str] = None  # 情志
    organ: Optional[str] = None  # 脏腑
    body_part: Optional[str] = None  # 身体部位
    sound: Optional[str] = None  # 五音
    element_strength: Optional[str] = None  # 五行强度
    he_luo_number: Optional[int] = None  # 河洛配数



class DizhiResponse(BaseModel):
    """地支响应模型"""
    id: str
    name: str
    order: int
    animal: str
    yin_yang: str
    wu_xing: str
    na_yin: str
    description: str

    # 新增属性
    cang_gan: Optional[List[str]] = None  # 藏干
    direction: Optional[str] = None  # 方位
    time_period: Optional[str] = None  # 时辰
    month: Optional[str] = None  # 月份
    season: Optional[str] = None  # 季节
    color: Optional[str] = None  # 颜色
    taste: Optional[str] = None  # 五味
    emotion: Optional[str] = None  # 情志
    organ: Optional[str] = None  # 脏腑
    body_part: Optional[str] = None  # 身体部位
    sound: Optional[str] = None  # 五音
    element_strength: Optional[str] = None  # 五行强度
    he_luo_number: Optional[int] = None  # 河洛配数

    class Config:
        from_attributes = True


class DizhiCombinationRequest(BaseModel):
    """地支组合请求模型"""
    dizhi1: str
    dizhi2: str


class DizhiCombinationResponse(BaseModel):
    """地支组合响应模型"""
    first_dizhi: str
    second_dizhi: str
    relation_type: str
    description: str
    is_valid: bool


class SanHeGroupRequest(BaseModel):
    """三合局请求模型"""
    dizhi1: str
    dizhi2: str
    dizhi3: str


class SanHeGroupResponse(BaseModel):
    """三合局响应模型"""
    dizhis: List[str]
    element: str
    description: str
    is_valid: bool


class DizhiRelationshipsResponse(BaseModel):
    """地支关系响应模型"""
    dizhi: DizhiResponse
    liu_he_partners: List[DizhiResponse]
    liu_chong_partners: List[DizhiResponse]
    san_he_partners: List[DizhiResponse]
    san_he_element: Optional[str] = None

# 依赖注入函数


def get_dizhi_service() -> DizhiService:
    """获取地支服务实例 - 这里应该从依赖注入容器获取"""
    from idp.projects.godata.master_data.infrastructure.repositories.memory_dizhi_repository import (
        MemoryDizhiRepository,
    )
    repository = MemoryDizhiRepository()
    return DizhiService(repository)


# 创建路由器
router = APIRouter(prefix="/dizhi", tags=["地支"])


@router.get("/", response_model=List[DizhiResponse], description="获取所有地支", tags=["地支"])
async def get_all_dizhis(
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取所有地支"""
    dizhis = await service.get_all_dizhis()
    return [DizhiResponse.from_orm(dizhi) for dizhi in dizhis]


@router.get("/{name}", response_model=DizhiResponse, description="根据名称获取地支", tags=["地支"])
async def get_dizhi_by_name(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """根据名称获取地支"""
    dizhi = await service.get_dizhi_by_name(name)
    if not dizhi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"地支 '{name}' 不存在"
        )
    return DizhiResponse.from_orm(dizhi)


@router.get("/order/{order}", response_model=DizhiResponse, description="根据序号获取地支")
async def get_dizhi_by_order(
    order: int,
    service: DizhiService = Depends(get_dizhi_service)
):
    """根据序号获取地支"""
    dizhi = await service.get_dizhi_by_order(order)
    if not dizhi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"序号为 {order} 的地支不存在"
        )
    return DizhiResponse.from_orm(dizhi)


@router.get("/wuxing/{wu_xing}", response_model=List[DizhiResponse], description="根据五行属性获取地支列表")
async def get_dizhis_by_wuxing(
    wu_xing: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """根据五行属性获取地支列表"""
    dizhis = await service.get_dizhis_by_wuxing(wu_xing)
    return [DizhiResponse.from_orm(dizhi) for dizhi in dizhis]


@router.get("/yin-yang/{yin_yang}", response_model=List[DizhiResponse], description="根据阴阳属性获取地支列表")
async def get_dizhis_by_yin_yang(
    yin_yang: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """根据阴阳属性获取地支列表"""
    if yin_yang == "阳":
        dizhis = await service.get_yang_dizhis()
    elif yin_yang == "阴":
        dizhis = await service.get_yin_dizhis()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="阴阳属性必须是 '阳' 或 '阴'"
        )
    return [DizhiResponse.from_orm(dizhi) for dizhi in dizhis]


@router.get("/animal/{animal}", response_model=List[DizhiResponse], description="根据生肖获取地支列表")
async def get_dizhis_by_animal(
    animal: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """根据生肖获取地支列表"""
    dizhis = await service.get_dizhis_by_animal(animal)
    return [DizhiResponse.from_orm(dizhi) for dizhi in dizhis]


@router.post("/", response_model=DizhiResponse, status_code=status.HTTP_201_CREATED, description="创建新的地支")
async def create_dizhi(
    request: DizhiCreateRequest,
    service: DizhiService = Depends(get_dizhi_service)
):
    """创建新的地支"""
    try:
        dizhi = await service.create_dizhi(
            name=request.name,
            order=request.order,
            animal=request.animal,
            yin_yang=request.yin_yang,
            wu_xing=request.wu_xing,
            na_yin=request.na_yin,
            description=request.description,
            cang_gan=request.cang_gan,
            direction=request.direction,
            time_period=request.time_period,
            month=request.month,
            season=request.season,
            color=request.color,
            taste=request.taste,
            emotion=request.emotion,
            organ=request.organ,
            body_part=request.body_part,
            sound=request.sound,
            element_strength=request.element_strength
        )
        return DizhiResponse.from_orm(dizhi)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# 六合关系相关接口


@router.post("/liu-he", response_model=DizhiCombinationResponse, description="检查两个地支是否六合")
async def check_liu_he(
    request: DizhiCombinationRequest,
    service: DizhiService = Depends(get_dizhi_service)
):
    """检查两个地支是否六合"""
    combination = await service.check_liu_he(
        request.dizhi1,
        request.dizhi2
    )

    if combination:
        return DizhiCombinationResponse(
            first_dizhi=combination.first_dizhi,
            second_dizhi=combination.second_dizhi,
            relation_type=combination.relation_type.value,
            description=combination.description,
            is_valid=True
        )
    else:
        return DizhiCombinationResponse(
            first_dizhi=request.dizhi1,
            second_dizhi=request.dizhi2,
            relation_type="",
            description=f"{request.dizhi1} 和 {request.dizhi2} 不六合",
            is_valid=False
        )


@router.get("/{name}/liu-he", response_model=List[DizhiResponse], description="获取与指定地支六合的地支列表")
async def get_liu_he_partners(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取与指定地支六合的地支列表"""
    partners = await service.get_liu_he_partners(name)
    return [DizhiResponse.from_orm(dizhi) for dizhi in partners]

# 六冲关系相关接口


@router.post("/liu-chong", response_model=DizhiCombinationResponse, description="检查两个地支是否六冲")
async def check_liu_chong(
    request: DizhiCombinationRequest,
    service: DizhiService = Depends(get_dizhi_service)
):
    """检查两个地支是否六冲"""
    combination = await service.check_liu_chong(
        request.dizhi1,
        request.dizhi2
    )

    if combination:
        return DizhiCombinationResponse(
            first_dizhi=combination.first_dizhi,
            second_dizhi=combination.second_dizhi,
            relation_type=combination.relation_type.value,
            description=combination.description,
            is_valid=True
        )
    else:
        return DizhiCombinationResponse(
            first_dizhi=request.dizhi1,
            second_dizhi=request.dizhi2,
            relation_type="",
            description=f"{request.dizhi1} 和 {request.dizhi2} 不六冲",
            is_valid=False
        )


@router.get("/{name}/liu-chong", response_model=List[DizhiResponse], description="获取与指定地支六冲的地支列表")
async def get_liu_chong_partners(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取与指定地支六冲的地支列表"""
    partners = await service.get_liu_chong_partners(name)
    return [DizhiResponse.from_orm(dizhi) for dizhi in partners]

# 三合关系相关接口


@router.post("/san-he", response_model=DizhiCombinationResponse, description="检查两个地支是否三合")
async def check_san_he(
    request: DizhiCombinationRequest,
    service: DizhiService = Depends(get_dizhi_service)
):
    """检查两个地支是否三合"""
    combination = await service.check_san_he(
        request.dizhi1,
        request.dizhi2
    )

    if combination:
        return DizhiCombinationResponse(
            first_dizhi=combination.first_dizhi,
            second_dizhi=combination.second_dizhi,
            relation_type=combination.relation_type.value,
            description=combination.description,
            is_valid=True
        )
    else:
        return DizhiCombinationResponse(
            first_dizhi=request.dizhi1,
            second_dizhi=request.dizhi2,
            relation_type="",
            description=f"{request.dizhi1} 和 {request.dizhi2} 不三合",
            is_valid=False
        )


@router.post("/san-he-group", response_model=SanHeGroupResponse, description="创建三合局")
async def create_san_he_group(
    request: SanHeGroupRequest,
    service: DizhiService = Depends(get_dizhi_service)
):
    """创建三合局"""
    san_he_group = await service.create_san_he_group(
        request.dizhi1,
        request.dizhi2,
        request.dizhi3
    )

    if san_he_group:
        return SanHeGroupResponse(
            dizhis=list(san_he_group.dizhis),
            element=san_he_group.element.value,
            description=san_he_group.get_description(),
            is_valid=True
        )
    else:
        return SanHeGroupResponse(
            dizhis=[request.dizhi1, request.dizhi2, request.dizhi3],
            element="",
            description=f"{request.dizhi1}{request.dizhi2}{request.dizhi3} 不能组成三合局",
            is_valid=False
        )


@router.get("/{name}/san-he", response_model=List[DizhiResponse], description="获取与指定地支三合的地支列表")
async def get_san_he_partners(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取与指定地支三合的地支列表"""
    partners = await service.get_san_he_partners(name)
    return [DizhiResponse.from_orm(dizhi) for dizhi in partners]


@router.get("/san-he-groups/all", response_model=List[SanHeGroupResponse], description="获取所有三合局")
async def get_all_san_he_groups(
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取所有三合局"""
    groups = await service.get_all_san_he_groups()
    return [
        SanHeGroupResponse(
            dizhis=list(group.dizhis),
            element=group.element.value,
            description=group.get_description(),
            is_valid=True
        ) for group in groups
    ]

# 综合关系查询接口


@router.get("/{name}/relationships", response_model=DizhiRelationshipsResponse, description="获取指定地支的所有关系")
async def get_dizhi_relationships(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取指定地支的所有关系"""
    relationships = await service.get_dizhi_relationships(name)
    if not relationships:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"地支 '{name}' 不存在"
        )

    return DizhiRelationshipsResponse(
        dizhi=DizhiResponse.from_orm(relationships["dizhi"]),
        liu_he_partners=[DizhiResponse.from_orm(
            dizhi) for dizhi in relationships["liu_he_partners"]],
        liu_chong_partners=[DizhiResponse.from_orm(
            dizhi) for dizhi in relationships["liu_chong_partners"]],
        san_he_partners=[DizhiResponse.from_orm(
            dizhi) for dizhi in relationships["san_he_partners"]],
        san_he_element=relationships["san_he_element"]
    )


@router.get("/{name}/next/{steps}", response_model=DizhiResponse, description="获取指定步数后的地支")
async def get_next_dizhi(
    name: str,
    steps: int = 1,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取指定步数后的地支"""
    next_dizhi = await service.get_next_dizhi_cycle(name, steps)
    if not next_dizhi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"地支 '{name}' 不存在"
        )
    return DizhiResponse.from_orm(next_dizhi)


@router.get("/{name}/cang-gan", response_model=dict, description="获取地支的藏干信息")
async def get_dizhi_cang_gan(
    name: str,
    service: DizhiService = Depends(get_dizhi_service)
):
    """获取地支的藏干信息"""
    dizhi = await service.get_dizhi_by_name(name)
    if not dizhi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"地支 '{name}' 不存在"
        )

    return {
        "dizhi": name,
        "all_cang_gan": dizhi.get_cang_gan(),
        "main_cang_gan": dizhi.get_main_cang_gan(),
        "qi_cang_gan": dizhi.get_qi_cang_gan(),
        "yu_cang_gan": dizhi.get_yu_cang_gan()
    }


@router.get("/{name}/shi-shen/{ri_gan}", response_model=dict, description="获取天干的十神关系")
async def get_tiangan_shi_shen(
    name: str,
    ri_gan: str,
    service: TianganService = Depends(get_tiangan_service)
):
    """获取天干的十神关系"""
    tiangan = await service.get_tiangan_by_name(name)
    if not tiangan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"天干 '{name}' 不存在"
        )

    shi_shen = tiangan.get_shi_shen(ri_gan)
    return {
        "tiangan": name,
        "ri_gan": ri_gan,
        "shi_shen": shi_shen
    }
