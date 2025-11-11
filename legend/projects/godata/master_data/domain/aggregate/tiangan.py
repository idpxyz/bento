
from typing import List, Optional

from idp.framework.domain.base import BaseAggregateRoot


class Tiangan(BaseAggregateRoot):
    """天干 - 中国传统历法中的十个天干"""
    id: str
    name: str  # 天干名称: 甲乙丙丁戊己庚辛壬癸
    order: int  # 天干序号: 1-10
    yin_yang: str  # 天干的阴阳属性: 阳干(甲丙戊庚壬), 阴干(乙丁己辛癸)
    wu_xing: str  # 天干的五行属性: 甲乙木, 丙丁火, 戊己土, 庚辛金, 壬癸水
    na_yin: str  # 天干的纳音: 甲己海中金, 乙庚炉中火, 丙辛白蜡金, 丁壬杨柳木, 戊癸井泉水
    description: str  # 天干的象征意义和作用
    he_hua: Optional[str] = None  # 天干的合化关系: 甲己合土, 乙庚合金, 丙辛合水, 丁壬合木, 戊癸合火

    # 新增属性
    direction: str  # 方位: 甲乙东, 丙丁南, 戊己中, 庚辛西, 壬癸北
    season: str  # 季节: 甲乙春, 丙丁夏, 戊己长夏, 庚辛秋, 壬癸冬
    color: str  # 颜色: 甲乙青, 丙丁红, 戊己黄, 庚辛白, 壬癸黑
    taste: str  # 五味: 甲乙酸, 丙丁苦, 戊己甘, 庚辛辛, 壬癸咸
    emotion: str  # 情志: 甲乙怒, 丙丁喜, 戊己思, 庚辛悲, 壬癸恐
    organ: str  # 脏腑: 甲乙肝胆, 丙丁心小肠, 戊己脾胃, 庚辛肺大肠, 壬癸肾膀胱
    body_part: str  # 身体部位: 甲乙筋, 丙丁脉, 戊己肉, 庚辛皮毛, 壬癸骨
    sound: str  # 五音: 甲乙角, 丙丁徵, 戊己宫, 庚辛商, 壬癸羽
    he_luo_number: int  # 河洛配数: 甲9, 乙8, 丙7, 丁6, 戊5, 己4, 庚3, 辛2, 壬1, 癸0

    def __init__(self, **kwargs):
        # 先设置属性
        for key, value in kwargs.items():
            setattr(self, key, value)
        # 然后调用父类构造函数
        super().__init__(**kwargs)
        # 最后进行验证
        self._validate_tiangan_properties()

    def _validate_tiangan_properties(self):
        """验证天干属性的合理性"""
        valid_names = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
        if self.name not in valid_names:
            raise ValueError(f"天干名称必须是: {valid_names}")

        if not 1 <= self.order <= 10:
            raise ValueError("天干序号必须在1-10之间")

        # 验证阴阳属性
        yang_gans = ['甲', '丙', '戊', '庚', '壬']
        yin_gans = ['乙', '丁', '己', '辛', '癸']
        if self.name in yang_gans and self.yin_yang != '阳':
            raise ValueError(f"{self.name}应该是阳干")
        if self.name in yin_gans and self.yin_yang != '阴':
            raise ValueError(f"{self.name}应该是阴干")

        # 验证五行属性
        wuxing_map = {
            '甲': '木', '乙': '木',
            '丙': '火', '丁': '火',
            '戊': '土', '己': '土',
            '庚': '金', '辛': '金',
            '壬': '水', '癸': '水'
        }
        if self.wu_xing != wuxing_map.get(self.name):
            raise ValueError(f"{self.name}的五行属性应该是{wuxing_map.get(self.name)}")

        # 验证方位属性
        direction_map = {
            '甲': '东', '乙': '东',
            '丙': '南', '丁': '南',
            '戊': '中', '己': '中',
            '庚': '西', '辛': '西',
            '壬': '北', '癸': '北'
        }
        if hasattr(self, 'direction') and self.direction != direction_map.get(self.name):
            raise ValueError(
                f"{self.name}的方位应该是{direction_map.get(self.name)}")

    def get_next_tiangan(self) -> 'Tiangan':
        """获取下一个天干"""
        next_order = (self.order % 10) + 1
        # 这里需要从仓储中获取下一个天干
        # 实际实现中需要依赖注入仓储
        pass

    def get_previous_tiangan(self) -> 'Tiangan':
        """获取上一个天干"""
        prev_order = 10 if self.order == 1 else self.order - 1
        # 这里需要从仓储中获取上一个天干
        pass

    def is_compatible_with(self, other_tiangan: 'Tiangan') -> bool:
        """判断两个天干是否相合"""
        he_hua_pairs = [
            ('甲', '己'), ('乙', '庚'), ('丙', '辛'),
            ('丁', '壬'), ('戊', '癸')
        ]
        return (self.name, other_tiangan.name) in he_hua_pairs or \
               (other_tiangan.name, self.name) in he_hua_pairs

    def get_shi_shen(self, ri_gan: str) -> str:
        """获取十神关系"""
        # 十神：比肩、劫财、食神、伤官、偏财、正财、七杀、正官、偏印、正印
        shi_shen_map = {
            '甲': {'甲': '比肩', '乙': '劫财', '丙': '食神', '丁': '伤官', '戊': '偏财',
                  '己': '正财', '庚': '七杀', '辛': '正官', '壬': '偏印', '癸': '正印'},
            '乙': {'甲': '劫财', '乙': '比肩', '丙': '食神', '丁': '伤官', '戊': '偏财',
                  '己': '正财', '庚': '七杀', '辛': '正官', '壬': '偏印', '癸': '正印'},
            '丙': {'甲': '偏印', '乙': '正印', '丙': '比肩', '丁': '劫财', '戊': '食神',
                  '己': '伤官', '庚': '偏财', '辛': '正财', '壬': '七杀', '癸': '正官'},
            '丁': {'甲': '偏印', '乙': '正印', '丙': '劫财', '丁': '比肩', '戊': '食神',
                  '己': '伤官', '庚': '偏财', '辛': '正财', '壬': '七杀', '癸': '正官'},
            '戊': {'甲': '七杀', '乙': '正官', '丙': '偏印', '丁': '正印', '戊': '比肩',
                  '己': '劫财', '庚': '食神', '辛': '伤官', '壬': '偏财', '癸': '正财'},
            '己': {'甲': '七杀', '乙': '正官', '丙': '偏印', '丁': '正印', '戊': '劫财',
                  '己': '比肩', '庚': '食神', '辛': '伤官', '壬': '偏财', '癸': '正财'},
            '庚': {'甲': '正财', '乙': '偏财', '丙': '七杀', '丁': '正官', '戊': '偏印',
                  '己': '正印', '庚': '比肩', '辛': '劫财', '壬': '食神', '癸': '伤官'},
            '辛': {'甲': '正财', '乙': '偏财', '丙': '七杀', '丁': '正官', '戊': '偏印',
                  '己': '正印', '庚': '劫财', '辛': '比肩', '壬': '食神', '癸': '伤官'},
            '壬': {'甲': '伤官', '乙': '食神', '丙': '正财', '丁': '偏财', '戊': '七杀',
                  '己': '正官', '庚': '偏印', '辛': '正印', '壬': '比肩', '癸': '劫财'},
            '癸': {'甲': '伤官', '乙': '食神', '丙': '正财', '丁': '偏财', '戊': '七杀',
                  '己': '正官', '庚': '偏印', '辛': '正印', '壬': '劫财', '癸': '比肩'}
        }
        return shi_shen_map.get(ri_gan, {}).get(self.name, '未知')
