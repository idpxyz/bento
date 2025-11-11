下面给出《**倪派紫微斗数计算引擎（Ni-ZWDS Engine）系统设计说明书**》。本说明书面向**工程实现**（Python、`sxtwl`≥2.x），将流派差异做成**可配置**与**可插拔策略**，保证可验证与可维护。

> 版本：v0.1（草案）
> 日期：2025-08-05
> 适用范围：后端计算引擎、API、数据表、测试与可视化

---

## 1. 目标与范围

**目标**

* 构建一套**可重现、可配置**的紫微斗数排盘与推运引擎，支持倪派常见口径（重点：**年干四化、宫干四化/飞宫四化**分层与**动盘层叠飞化**），并提供**工程化 API**、**数据表版本化**与**可视化**。
* 与\*\*`sxtwl`≥2.x**历法引擎集成，精确获得**节气（含立春）时刻、干支、农历信息、儒略日\*\*等历算基础能力。 ([PyPI][1], [CSDN Blog][2])

**范围**

* **静盘**：命/身宫、宫干、主辅星安置、年干四化、宫干四化/飞宫四化。
* **动盘**：大限/小限/流年/流月/流日（阳男阴女顺、阴男阳女逆；五行局起限可选）。 ([Douban][3], [iztro.com][4], [m.ximalaya.com][5])
* **解释**：三方四正、格局/会照规则引擎；飞化事件链路可视化。 ([Zhihu][6])
* **接口**：REST/CLI/文件输出（JSON、SVG/PNG）。

**不在本期**

* 前端 UI 与命理解读文案库的全面化（仅提供结构化“证据点”）。
* 争议口径的判定归一（通过**多版本表**与**并行排盘对照**解决）。

---

## 2. 术语与关键概念（工程口径）

* **四化**：化禄/化权/化科/化忌。分 **生年四化**（按年干）、**宫干四化/飞宫四化**（按各宫天干引发的飞入/自化）、以及**各层限的四化**。这是飞星派/实占的**核心分层**。 ([Ziwei][7], [360doc][8])
* **三方四正**：本宫＋两三合宫为“三方”，再加对宫为“四正”，解释影响需查看四宫联动。 ([Zhihu][6])
* **大限方向**：通用规则“**阳男阴女顺行、阴男阳女逆行**”。起限与步长受**五行局**影响（常见首限起岁：2/3/4/5/6）。 ([Douban][3], [m.ximalaya.com][5])
* **命宫/身宫起法**：通用默认为“**寅起正月**，以**月+时**定命宫/身宫”的系列起法（存在细分变体）。 ([360doc][9], [i.ifeng.com][10])
* **时间基准**：可在**当地民用时**与**真太阳时**间切换（真太阳时使用**地理经度修正＋均时差**等因子）。 ([Wikipedia][11], [Zhihu][12])

---

## 3. 需求说明

### 3.1 功能需求

1. **历法计算（Calendars）**

   * 输入：出生地（经纬度）、出生时间（时区/DST）、性别。
   * 输出：干支（年/月/日/时）、节气（含**立春**精确时刻）、农历信息、儒略日。 ([PyPI][1], [CSDN Blog][2])
2. **边界与策略**

   * 年界：`lunar_newyear | lichun | jan1`（默认 `lunar_newyear`，支持**立春分年**对照）。
   * 月界：`lunar_month | solar_term_month`。
   * 时间基准：`civil_time | true_solar_time`（默认 `civil_time`）。 ([Wikipedia][11])
   * 命/身宫策略：`month_plus_hour`（寅起）等。
3. **星曜安置**

   * 主星14＋辅星系表驱动安置（多版本）。
4. **四化引擎**

   * 年干四化（先天）；宫干四化/飞宫四化（后天）；大限/流年/流月/流日分层叠加。 ([Ziwei][7])
5. **运限引擎**

   * 大限：阳男阴女顺、阴男阳女逆；首限起岁可选（常见“五行局 2/3/4/5/6”）。 ([Douban][3], [m.ximalaya.com][5])
   * 小限、流年、流月、流日：依序层叠与四化注入。
6. **规则与解释**

   * 三方四正联动识别；常见格局谓词；四化冲会/夹会识别。 ([Zhihu][6])
7. **接口与输出**

   * REST API、CLI；返回**结构化盘态**、**飞化事件流**、**可视化图层**（SVG/PNG）。

### 3.2 非功能需求

* **可配置与版本化**：四化表、安星表、起法策略**外部化**（YAML/JSON）。
* **可验证**：提供**样例盘回归测试**与**双方案对照报告**（如“农历年界 vs 立春年界”）。
* **性能**：单盘静盘≤50 ms；全栈（含多层飞化）≤150 ms（参考配置：8 vCPU）。
* **可观测**：结构化日志、指标（盘时长、表加载时间、策略命中率）。
* **国际化**：简体/繁体/英文星名映射。
* **安全**：输入校验与审计、禁存敏感个人数据。

---

## 4. 总体架构

```
+-------------------+       +----------------------+
|   Adapters/API    | <---> |   Application Layer  |
| REST / CLI / SDK  |       |  UseCases / Orchestr |
+-------------------+       +----------------------+
            |                           |
            v                           v
+-------------------+       +----------------------+
|   Engine Core     |       |    Rules Engine      |
| - Star Placer     |       | - 三方四正/格局谓词  |
| - Transform (SiHua)|      | - 冲会/夹会/飞化链   |
| - Limits (DaXian) |       +----------------------+
+-------------------+
            |
            v
+-------------------+       +----------------------+
|   Calendars       |       |   Tables Repository  |
| (sxtwl wrapper)   |       |  (YAML/JSON, version)|
+-------------------+       +----------------------+
```

数据流：输入→历法→命/身宫与宫干→星曜安置→四化分层→运限层叠→规则解释→输出/可视化。

---

## 5. 配置总表（示例）

```yaml
# config.yml
year_boundary: lunar_newyear   # or lichun | jan1
month_boundary: lunar_month    # or solar_term_month
time_basis: civil_time         # or true_solar_time (使用均时差/EoT)
ming_gong_strategy: month_plus_hour_ni_v1
shen_gong_strategy: hour_only_v1
daxian:
  direction: gender_stem_rule  # 阳男阴女顺、阴男阳女逆
  start_age_strategy: wuxing_2_3_4_5_6
tables:
  star_tables_version: "std-2025.07"
  sihua_version: "v1-ni-compatible"   # 十天干→禄权科忌 映射版本
  palace_stems_rule: "wuhu_dun"       # 年干→寅宫天干→顺排宫干
viz:
  theme: "classic"
```

> 说明：`true_solar_time` 需使用**地理经度修正＋均时差（Equation of Time, EoT）**；均时差与真太阳时的换算可参考天文学定义。 ([Wikipedia][11], [Zhihu][12])

---

## 6. 历法与时间基座（`sxtwl`集成）

* **库选择**：`sxtwl` 提供农历、公历互转、干支、节气（含交节时刻）、儒略日等接口，2.x 通过 SWIG 暴露至 Python。安装：`pip install sxtwl`。 ([PyPI][1])
* **封装**：`calendars/` 模块提供：

  * `get_li_chun(year, tz, lon, lat)`：立春本地时刻；
  * `get_ganzhi(dt, basis)`：年/月/日/时干支（支持民用时/真太阳时）；
  * `get_lunar_info(dt)`：农历年/月/闰月信息；
  * `jd(dt)`：儒略日。
* **年/月界策略**：

  * `year_boundary="lunar_newyear"` 或 `lichun`；
  * `month_boundary="lunar_month"` 或 `solar_term_month`（节令月）。
* **真太阳时（可选）**：

  * `true_solar_time = civil_time + longitude_offset + equation_of_time [+ dst_adj]`；
  * 其中**均时差**定义与计算见天文学文献（EoT）。 ([Wikipedia][11])

> 注：部分命理体系（如**四柱八字**）常以**立春**分年，因此引擎需支持**立春/农历正月初一**两种年界，用于**对照验证**。示例资料亦提到“八字以立春为年界”的实践。 ([Aliyun Developer Community][13])

---

## 7. 命宫/身宫与宫干

### 7.1 起法（默认）

* **命宫**：**寅起正月**，先以**月**定位，再以**时**回拨定位命宫（常见“月+时”法，存在若干变体）。 ([360doc][9], [i.ifeng.com][10])
* **身宫**：随时支落入规定阳宫（或依“月+时”另一套规则），保留多策略切换。 ([Douban][14])

### 7.2 宫干（天干）排入

* 以**生年天干**按**五虎遁**推出**寅宫天干**，再按天干顺序环排十二宫之**宫干**（常见口径）。 ([Douban][3])

---

## 8. 星曜安置（表驱动）

* **主星14**、**辅星系**（左/右、昌/曲、魁/钺、禄存、羊/陀、火/铃、空/劫、喜/鸾、刑/姚、马/解等）均以**规则表**安置：

  * `tables/stars/{version}/main.yaml`
  * `tables/stars/{version}/aux.yaml`
* 引擎入口：`place_stars(birth, chrono, tables, strategies) -> palace_of[star]`。

---

## 9. 四化引擎（SiHua Engine）

### 9.1 分层模型

1. **生年四化**（年干→禄/权/科/忌；先天）
2. **宫干四化/飞宫四化**（各宫天干触发的飞入/自化；后天核心）
3. **运限层四化**：大限/流年/流月/流日按其层的“年干/宫干”触发，**层层叠加**

> 分层、回归、生年四化为根、宫干自化与飞星关联的思路见多处学习资料。 ([Ziwei][7], [360doc][8])

### 9.2 事件模型（统一数据结构）

```json
{
  "level": "natal|decade|year|month|day",
  "source": "year_gan|palace:<宫>|limit:<年份/限段>",
  "star": "文昌",
  "type": "禄|权|科|忌",
  "mode": "in|out|self",             // 飞入/飞出/自化
  "from": "命宫",
  "to": "财帛宫",
  "links": ["三方四正:命-财-官-迁"]
}
```

### 9.3 冲突与聚合

* 同层多次四化→按**表顺序**与**优先级**去重合并；
* 跨层叠加→按 `natal -> decade -> year -> month -> day` 合并，保留**证据链**。

### 9.4 四化表（版本化）

* `tables/sihua/{version}.yaml`：**十天干→禄/权/科/忌**映射存在版本差异，需**多版本并存**与**测试对照**。示例表可参见公开资料整理。 ([Ziwei][7])

---

## 10. 运限引擎（Limits Engine）

* **方向**：`阳男阴女顺`、`阴男阳女逆` 为默认（可切换）。 ([Douban][3], [iztro.com][4])
* **首限起算**：默认采用“五行局 2/3/4/5/6 岁起限”（亦提供“周岁整十段”作为兼容选项）。 ([m.ximalaya.com][5])
* **步长与落宫**：每十年一限，按方向推进宫位；各层（年/月/日）按序注入四化。
* **小限**：按常见规则“男顺女逆”提供策略开关。

---

## 11. 规则引擎与解释输出

* **三方四正**：本宫＋财帛＋官禄＋迁移四宫联动的识别与高亮。 ([Zhihu][6])
* **格局识别**：如杀破狼、紫府朝垣、机月同梁、日月照壁等（以谓词组合定义）。
* **冲会/夹会**：禄权夹命、忌入×宫、科权解忌等模式库。
* **输出**：结构化“证据点”＋简明文本（避免主观化）。

---

## 12. 数据模型（核心）

```python
class BirthInfo(BaseModel):
    dt_local: datetime
    tz: str
    lat: float
    lon: float
    gender: Literal["M","F"]
    use_true_solar_time: bool = False

class ChronoKeys(BaseModel):
    year_gz: str
    month_key: str         # lunar_5 / solar_term_mN
    day_gz: str
    hour_zhi: str
    lichun_dt: datetime
    jd: float

class ChartState(BaseModel):
    palace_of: dict[str, str]   # 星曜 -> 宫位
    palace_stems: dict[str, str]# 宫位 -> 天干
    transforms: list[TransformEvent]
    meta: dict

class TransformEvent(BaseModel):
    level: str; source: str; star: str; type: str
    mode: str; from_palace: str|None; to_palace: str|None
    links: list[str]
```

---

## 13. API 设计（REST，示例）

```
POST /api/v1/chart/compute
Body:
{
  "birth": { "dtLocal": "1983-09-02T06:17:00", "tz": "Asia/Shanghai",
             "lat": 38.93, "lon": 100.45, "gender": "M" },
  "options": {
    "yearBoundary": "lichun",
    "monthBoundary": "lunar_month",
    "timeBasis": "civil_time",
    "mingGongStrategy": "month_plus_hour_ni_v1",
    "daxian": { "direction": "gender_stem_rule", "startAge": "wuxing_2_3_4_5_6" },
    "tables": { "stars": "std-2025.07", "sihua": "v1-ni-compatible" }
  },
  "levels": ["natal","decade","year"]
}
```

**响应**：`ChartState`、每层**四化事件流**、三方四正关系、SVG 可视化（Base64）。

---

## 14. 可视化与导出

* **宫盘**：12宫环形图、宫干标注、主辅星、三方四正高亮。
* **飞化链路**：箭头（in/out/self），按层筛选叠加。
* **导出**：SVG/PNG；结构化 JSON（可二次计算）。

---

## 15. 表与策略的版本管理

```
tables/
  stars/std-2025.07/{main.yaml, aux.yaml}
  sihua/v1-ni-compatible.yaml
  sihua/v2-common.yaml
strategies/
  ming_gong/month_plus_hour_ni_v1.py
  shen_gong/hour_only_v1.py
  daxian/wuxing_2_3_4_5_6.py
```

* **变更即测试**：任何表/策略变更必须触发**回归套件**与**对照报告**。

---

## 16. 测试与验收

* **单元测试**：历法键值、命/身宫、宫干、四化事件、运限推进。
* **黄金样例**：收集2–3套**跨立春**、含**闰月**样例盘，确保**双年界对照**与**四化一致性**。
* **比对校核**：与公开计算说明/教学资料进行星位与四化链路核验（负责任地标注来源差异）。

---

## 17. 运维与质量

* **日志**：结构化（盘ID、配置签名、时耗、表版本）。
* **指标**：P95 计算延迟、错误率、策略命中分布。
* **灰度**：新表/新策略先灰度 10%，比对差异后全量。
* **安全与隐私**：仅存储**经纬度粗化**与**时间窗口脱敏**（可选），不落个人身份信息。

---

## 18. 已知争议与风险控制

* **年界差异**：农历正月初一 vs **立春** vs 公历 1/1 → 以**开关**与**对照报告**化解（八字中常见立春分年，故需兼容）。 ([Aliyun Developer Community][13])
* **真太阳时**：是否启用影响小时支与宫位定位 → 默认**民用时**，开启时基于**均时差/EoT**精确换算。 ([Wikipedia][11], [Zhihu][12])
* **四化表版本**：存在差异 → **多版本并存**，以测试与证据链输出确保可追溯。 ([Ziwei][7])
* **大限首限**：五行局起岁 vs 周岁整十段 → 策略化可切，默认前者（常见口径）。 ([m.ximalaya.com][5])

---

## 19. 里程碑

1. **M1（1周）**：`sxtwl` 封装、年/月界与时间基准开关；样例接口返回干支/节气键值。 ([PyPI][1])
2. **M2（2周）**：命/身宫策略、宫干（五虎遁）与主星安置；四化表加载（年四化）。 ([Douban][3])
3. **M3（2周）**：宫干四化/飞宫四化、事件模型与三方四正规则。 ([Ziwei][7], [Zhihu][6])
4. **M4（2周）**：大限/流年层叠与可视化、对照报告。 ([Douban][3])
5. **M5（1周）**：回归测试、性能优化与文档化交付。

---

## 20. 附录

### 20.1 关键算法草图

**命宫（月+时，寅起）**

```
idx_month = (lunar_month - 1)                  # 寅为1，一路顺排
pal_month_palace = rotate_from("寅", +idx_month)
idx_hour = index_of_zhi(hour_zhi)              # 子=0, 丑=1, ...
ming_palace = rotate_from(pal_month_palace, -idx_hour)
```

> 起法存在变体，默认采用“寅起正月、月+时”常见法。 ([360doc][9], [i.ifeng.com][10])

**宫干（五虎遁）**

```
yin_gan = wuhu_dun(year_heavenly_stem)         # 推寅宫天干
palace_stems = cycle_from(yin_gan, order="甲乙丙丁戊己庚辛壬癸")
```

> “以年干推寅宫天干再顺排”可见常见教学说明。 ([Douban][3])

**四化叠加**

```
events = []
events += year_sihua(year_gan, table)          # 先天
events += palace_sihua(palace_stems, table)    # 后天
events += limit_sihua(decade/year/month/day)   # 动盘层
aggregate(events, precedence=[natal, decade, year, month, day])
```

> 生年四化、宫干自化/飞宫与层叠飞化的综合使用见学习资料。 ([Ziwei][7])

**大限方向与首限**

```
direction = "cw"  if is_yang_male_or_yin_female(year_gan, gender) else "ccw"
start_age = {水:2, 木:3, 金:4, 土:5, 火:6}[wuxing_ju]
```

> “阳男阴女顺、阴男阳女逆”与“五行局 2/3/4/5/6 岁起限”为常见规则描述。 ([Douban][3], [m.ximalaya.com][5])

---

## 参考与资料（节选）

* `sxtwl`（PyPI/安装与简介）与使用示例。([PyPI][1], [CSDN Blog][2])
* 四化分层（生年四化、宫干自化/飞宫四化）学习材料。([Ziwei][7], [360doc][8])
* 大限方向与解释（阳男阴女顺、阴男阳女逆）。([Douban][3], [iztro.com][4])
* 五行局与首限起岁示例。([m.ximalaya.com][5])
* 三方四正入门说明。([Zhihu][6])
* 命/身宫“寅起正月、月+时”常见起法说明。([360doc][9], [i.ifeng.com][10])
* 真太阳时与均时差（Equation of Time, EoT）。([Wikipedia][11], [Zhihu][12])

---

### 下一步请确认

1. **默认年界**（建议：`lunar_newyear`，同时提供`lichun`对照）。
2. **时间基准**（默认民用时；是否启用真太阳时）。
3. **四化表版本**（先用“v1-ni-compatible”占位，后可替换为你的指定表）。
4. **命/身宫与大限策略**（是否采用文中默认）。

你拍板后，我按本设计直接产出**基础代码骨架＋样例API＋两套年界对照报告**，并配齐单元测试。

[1]: https://pypi.org/project/sxtwl/?utm_source=chatgpt.com "sxtwl"
[2]: https://blog.csdn.net/weixin_44374471/article/details/126297669?utm_source=chatgpt.com "python：sxtwl（日历库） 原创"
[3]: https://m.douban.com/note/832984178/?utm_source=chatgpt.com "紫微斗数：中宫显示的阳男、阳女、阴男、阴女是什么意思？"
[4]: https://iztro.com/learn/basis?utm_source=chatgpt.com "紫微斗数基础"
[5]: https://m.ximalaya.com/ask/a8705539?utm_source=chatgpt.com "紫微斗数大限盘怎么排，是看大运的地支所在的宫位"
[6]: https://zhuanlan.zhihu.com/p/661859470?utm_source=chatgpt.com "紫微斗数解盘必备技能：看懂三方四正"
[7]: https://www.ziwei.my/si-hua/sheng-nian-si-hua-gong-gan-si-hua-fei-xing-si-hua/?utm_source=chatgpt.com "生年四化、宫干自化及飞星四化"
[8]: https://www.360doc.com/content/23/1013/17/14493421_1100075968.shtml?utm_source=chatgpt.com "如何区分飞星盘中的生年四化、命宫四化与飞宫四化？"
[9]: https://www.360doc.com/content/24/0704/10/72381642_1127829253.shtml?utm_source=chatgpt.com "紫微斗数安星法：如何定紫微星"
[10]: https://i.ifeng.com/c/88GYalsubuU?utm_source=chatgpt.com "李凯凯老师讲紫微斗数：命宫和身宫的秘密"
[11]: https://zh.wikipedia.org/zh-hans/%E5%9D%87%E6%99%82%E5%B7%AE?utm_source=chatgpt.com "均时差- 维基百科，自由的百科全书"
[12]: https://www.zhihu.com/question/629708022?utm_source=chatgpt.com "如何用一条简单公式计算真太阳时？"
[13]: https://developer.aliyun.com/article/691282?utm_source=chatgpt.com "使用python排八字计算八字的相合相冲五行分值等"
[14]: https://m.douban.com/note/833510269/?utm_source=chatgpt.com "紫微斗数：排出命盘十二宫和身宫的方法和步骤"
