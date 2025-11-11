from typing import List, Optional

from idp.framework.domain.base import BaseAggregateRoot


class Dizhi(BaseAggregateRoot):
    """地支 - 中国传统历法中的十二地支"""
    id: str
    name: str  # 地支名称: 子丑寅卯辰巳午未申酉戌亥
    order: int  # 地支序号: 1-12
    animal: str  # 地支对应的动物: 鼠牛虎兔龙蛇马羊猴鸡狗猪
    yin_yang: str  # 地支的阴阳属性: 阳支(子寅辰午申戌), 阴支(丑卯巳未酉亥)
    wu_xing: str  # 地支的五行属性
    na_yin: str  # 地支的纳音
    description: str  # 地支的象征意义和作用

    # 新增属性
    # 藏干: 子藏癸, 丑藏己辛癸, 寅藏甲丙戊, 卯藏乙, 辰藏戊乙癸, 巳藏丙庚戊, 午藏丁己, 未藏己丁乙, 申藏庚壬戊, 酉藏辛, 戌藏戊辛丁, 亥藏壬甲
    cang_gan: List[str]
    direction: str  # 方位: 子北, 丑东北, 寅东北, 卯东, 辰东南, 巳东南, 午南, 未西南, 申西南, 酉西, 戌西北, 亥西北
    # 时辰: 子时(23-1), 丑时(1-3), 寅时(3-5), 卯时(5-7), 辰时(7-9), 巳时(9-11), 午时(11-13), 未时(13-15), 申时(15-17), 酉时(17-19), 戌时(19-21), 亥时(21-23)
    time_period: str
    month: str  # 月份: 子十一月, 丑十二月, 寅正月, 卯二月, 辰三月, 巳四月, 午五月, 未六月, 申七月, 酉八月, 戌九月, 亥十月
    season: str  # 季节: 子丑冬, 寅卯春, 辰巳夏, 午未夏, 申酉秋, 戌亥冬
    color: str  # 颜色: 子亥黑, 丑辰未戌黄, 寅卯青, 巳午红, 申酉白
    taste: str  # 五味: 子亥咸, 丑辰未戌甘, 寅卯酸, 巳午苦, 申酉辛
    emotion: str  # 情志: 子亥恐, 丑辰未戌思, 寅卯怒, 巳午喜, 申酉悲
    organ: str  # 脏腑: 子亥肾膀胱, 丑辰未戌脾胃, 寅卯肝胆, 巳午心小肠, 申酉肺大肠
    body_part: str  # 身体部位: 子亥骨, 丑辰未戌肉, 寅卯筋, 巳午脉, 申酉皮毛
    sound: str  # 五音: 子亥羽, 丑辰未戌宫, 寅卯角, 巳午徵, 申酉商
    element_strength: str  # 五行强度: 旺、相、休、囚、死
    he_luo_number: int  # 河洛配数: 子9, 丑8, 寅7, 卯6, 辰5, 巳4, 午9, 未8, 申7, 酉6, 戌5, 亥4

    def __init__(self, **kwargs):
        # 先设置属性
        for key, value in kwargs.items():
            setattr(self, key, value)
        # 然后调用父类构造函数
        super().__init__(**kwargs)
        # 最后进行验证
        self._validate_dizhi_properties()

    def _validate_dizhi_properties(self):
        """验证地支属性的合理性"""
        valid_names = ['子', '丑', '寅', '卯', '辰',
                       '巳', '午', '未', '申', '酉', '戌', '亥']
        if self.name not in valid_names:
            raise ValueError(f"地支名称必须是: {valid_names}")

        if not 1 <= self.order <= 12:
            raise ValueError("地支序号必须在1-12之间")

        # 验证动物属性
        animal_map = {
            '子': '鼠', '丑': '牛', '寅': '虎', '卯': '兔',
            '辰': '龙', '巳': '蛇', '午': '马', '未': '羊',
            '申': '猴', '酉': '鸡', '戌': '狗', '亥': '猪'
        }
        if self.animal != animal_map.get(self.name):
            raise ValueError(f"{self.name}对应的动物应该是{animal_map.get(self.name)}")

        # 验证阴阳属性
        yang_zhi = ['子', '寅', '辰', '午', '申', '戌']
        yin_zhi = ['丑', '卯', '巳', '未', '酉', '亥']
        if self.name in yang_zhi and self.yin_yang != '阳':
            raise ValueError(f"{self.name}应该是阳支")
        if self.name in yin_zhi and self.yin_yang != '阴':
            raise ValueError(f"{self.name}应该是阴支")

        # 验证五行属性
        wuxing_map = {
            '子': '水', '丑': '土', '寅': '木', '卯': '木',
            '辰': '土', '巳': '火', '午': '火', '未': '土',
            '申': '金', '酉': '金', '戌': '土', '亥': '水'
        }
        if self.wu_xing != wuxing_map.get(self.name):
            raise ValueError(f"{self.name}的五行属性应该是{wuxing_map.get(self.name)}")

    def get_liu_he_partner(self) -> Optional[str]:
        """获取六合伙伴"""
        liu_he_pairs = {
            '子': '丑', '丑': '子',
            '寅': '亥', '亥': '寅',
            '卯': '戌', '戌': '卯',
            '辰': '酉', '酉': '辰',
            '巳': '申', '申': '巳',
            '午': '未', '未': '午'
        }
        return liu_he_pairs.get(self.name)

    def get_liu_chong_partner(self) -> Optional[str]:
        """获取六冲伙伴"""
        liu_chong_pairs = {
            '子': '午', '午': '子',
            '丑': '未', '未': '丑',
            '寅': '申', '申': '寅',
            '卯': '酉', '酉': '卯',
            '辰': '戌', '戌': '辰',
            '巳': '亥', '亥': '巳'
        }
        return liu_chong_pairs.get(self.name)

    def get_san_he_partners(self) -> List[str]:
        """获取三合伙伴"""
        san_he_groups = [
            ['寅', '午', '戌'],  # 火局
            ['亥', '卯', '未'],  # 木局
            ['巳', '酉', '丑'],  # 金局
            ['申', '子', '辰']   # 水局
        ]

        for group in san_he_groups:
            if self.name in group:
                return [zhi for zhi in group if zhi != self.name]
        return []

    def get_san_he_element(self) -> Optional[str]:
        """获取三合局对应的五行"""
        san_he_elements = {
            '寅': '火', '午': '火', '戌': '火',  # 火局
            '亥': '木', '卯': '木', '未': '木',  # 木局
            '巳': '金', '酉': '金', '丑': '金',  # 金局
            '申': '水', '子': '水', '辰': '水'   # 水局
        }
        return san_he_elements.get(self.name)

    def is_liu_he_with(self, other_dizhi: 'Dizhi') -> bool:
        """判断是否与另一个地支六合"""
        return self.get_liu_he_partner() == other_dizhi.name

    def is_liu_chong_with(self, other_dizhi: 'Dizhi') -> bool:
        """判断是否与另一个地支六冲"""
        return self.get_liu_chong_partner() == other_dizhi.name

    def is_san_he_with(self, other_dizhi: 'Dizhi') -> bool:
        """判断是否与另一个地支三合"""
        return other_dizhi.name in self.get_san_he_partners()

    def get_next_dizhi(self) -> 'Dizhi':
        """获取下一个地支"""
        next_order = (self.order % 12) + 1
        # 这里需要从仓储中获取下一个地支
        # 实际实现中需要依赖注入仓储
        pass

    def get_previous_dizhi(self) -> 'Dizhi':
        """获取上一个地支"""
        prev_order = 12 if self.order == 1 else self.order - 1
        # 这里需要从仓储中获取上一个地支
        pass

    def get_cang_gan(self) -> List[str]:
        """获取藏干"""
        cang_gan_map = {
            '子': ['癸'],
            '丑': ['己', '辛', '癸'],
            '寅': ['甲', '丙', '戊'],
            '卯': ['乙'],
            '辰': ['戊', '乙', '癸'],
            '巳': ['丙', '庚', '戊'],
            '午': ['丁', '己'],
            '未': ['己', '丁', '乙'],
            '申': ['庚', '壬', '戊'],
            '酉': ['辛'],
            '戌': ['戊', '辛', '丁'],
            '亥': ['壬', '甲']
        }
        return cang_gan_map.get(self.name, [])

    def get_main_cang_gan(self) -> str:
        """获取主气藏干"""
        main_cang_gan_map = {
            '子': '癸', '丑': '己', '寅': '甲', '卯': '乙',
            '辰': '戊', '巳': '丙', '午': '丁', '未': '己',
            '申': '庚', '酉': '辛', '戌': '戊', '亥': '壬'
        }
        return main_cang_gan_map.get(self.name, '')

    def get_qi_cang_gan(self) -> str:
        """获取中气藏干"""
        qi_cang_gan_map = {
            '子': '', '丑': '辛', '寅': '丙', '卯': '',
            '辰': '乙', '巳': '庚', '午': '己', '未': '丁',
            '申': '壬', '酉': '', '戌': '辛', '亥': '甲'
        }
        return qi_cang_gan_map.get(self.name, '')

    def get_yu_cang_gan(self) -> str:
        """获取余气藏干"""
        yu_cang_gan_map = {
            '子': '', '丑': '癸', '寅': '戊', '卯': '',
            '辰': '癸', '巳': '戊', '午': '', '未': '乙',
            '申': '戊', '酉': '', '戌': '丁', '亥': ''
        }
        return yu_cang_gan_map.get(self.name, '')

    def is_he_with(self, other_dizhi: 'Dizhi') -> bool:
        """判断是否与另一个地支相合（六合、三合、半合）"""
        return (self.is_liu_he_with(other_dizhi) or
                self.is_san_he_with(other_dizhi))

    def is_chong_with(self, other_dizhi: 'Dizhi') -> bool:
        """判断是否与另一个地支相冲（六冲）"""
        return self.is_liu_chong_with(other_dizhi)

    def get_relationship_with(self, other_dizhi: 'Dizhi') -> str:
        """获取与另一个地支的关系"""
        if self.is_liu_he_with(other_dizhi):
            return "六合"
        elif self.is_liu_chong_with(other_dizhi):
            return "六冲"
        elif self.is_san_he_with(other_dizhi):
            return "三合"
        else:
            return "无特殊关系"
