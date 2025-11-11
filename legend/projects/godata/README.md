# 八卦纳甲映射系统 (Trigram Najia Mapping System)

一个完整的八卦纳甲映射系统，实现了八卦与天干的对应关系，包括方位、符号和关系计算。

## 功能特性

### 🎯 核心功能
- **八卦天干映射**: 完整的八卦与天干对应关系
- **方位系统**: 后天八卦方位映射
- **符号支持**: 八卦符号（☰☷☳☴☵☲☶☱）显示
- **关系计算**: 八卦间的对冲、相邻等关系判断
- **循环顺序**: 后天八卦的循环变化顺序

### 📊 数据导出
- JSON格式导出
- CSV格式数据
- Markdown表格生成
- 完整映射表打印

### 🧪 测试覆盖
- 单元测试覆盖所有功能
- 性能测试
- 数据一致性验证

## 项目结构

```
godata/
├── src/
│   ├── __init__.py           # 包初始化文件
│   └── trigram_najia.py      # 核心实现
├── tests/
│   └── test_najia.py         # 测试文件
├── examples/
│   └── najia_example.py      # 使用示例
├── docs/
│   └── 八卦纳甲.md           # 文档和图表
├── run_najia.py              # 主程序运行脚本
├── run_tests.py              # 测试运行脚本
├── pyproject.toml            # 项目配置
└── README.md                 # 项目说明
```

## 快速开始

### 安装依赖
```bash
# 本项目使用Python标准库，无需额外安装依赖
python --version  # 建议Python 3.7+
```

### 运行程序
```bash
# 方法1: 使用运行脚本（推荐）
python run_najia.py

# 方法2: 直接运行主程序
python src/trigram_najia.py

# 方法3: 运行使用示例
PYTHONPATH=src python examples/najia_example.py
```

### 运行测试
```bash
# 方法1: 使用测试脚本（推荐）
python run_tests.py

# 方法2: 直接运行测试
PYTHONPATH=src python tests/test_najia.py
```

## 核心类说明

### NajiaMapping
主要的映射类，提供八卦与天干的对应关系。

```python
from src.trigram_najia import NajiaMapping, Trigram, HeavenlyStem

# 创建映射实例
mapping = NajiaMapping()

# 查询八卦对应的天干
stems = mapping.get_stems_for_trigram(Trigram.QIAN)  # [甲, 壬]

# 查询天干对应的八卦
trigram = mapping.get_trigram_for_stem(HeavenlyStem.JIA)  # 乾

# 查询八卦方位
direction = mapping.get_direction_for_trigram(Trigram.KAN)  # 北方

# 获取八卦符号
symbol = mapping.get_trigram_symbol(Trigram.QIAN)  # ☰
```

### NajiaCalculator
计算器类，提供八卦关系计算功能。

```python
from src.trigram_najia import NajiaCalculator

calculator = NajiaCalculator()

# 计算八卦关系
relationship = calculator.calculate_trigram_relationship(
    Trigram.KAN, Trigram.LI
)  # "对冲"
```

## 纳甲映射规则

### 八卦天干对应
| 八卦 | 符号 | 天干 | 方位 |
|------|------|------|------|
| 乾 | ☰ | 甲、壬 | 西北 |
| 坤 | ☷ | 乙、癸 | 西南 |
| 震 | ☳ | 庚 | 东方 |
| 巽 | ☴ | 辛 | 东南 |
| 坎 | ☵ | 戊 | 北方 |
| 离 | ☲ | 己 | 南方 |
| 艮 | ☶ | 丙 | 东北 |
| 兑 | ☱ | 丁 | 西方 |

### 后天八卦方位
```
        北方(坎)
   西北(乾)    东北(艮)
西方(兑)        东方(震)
   西南(坤)    东南(巽)
        南方(离)
```

## 使用示例

### 基础查询
```python
# 查询乾卦信息
trigram = Trigram.QIAN
stems = mapping.get_stems_for_trigram(trigram)
direction = mapping.get_direction_for_trigram(trigram)
symbol = mapping.get_trigram_symbol(trigram)

print(f"八卦: {trigram.value}（{symbol}）")
print(f"天干: {[stem.value for stem in stems]}")
print(f"方位: {direction.value}")
```

### 关系计算
```python
# 计算坎离关系
relationship = calculator.calculate_trigram_relationship(
    Trigram.KAN, Trigram.LI
)
print(f"坎离关系: {relationship}")  # 对冲
```

### 数据导出
```python
# 导出到JSON文件
mapping.export_to_json("najia_mapping.json")

# 获取完整映射数据
mapping_data = mapping.get_complete_mapping()
```

### 循环顺序分析
```python
# 获取后天八卦循环顺序
circular_order = mapping.get_circular_order()
for i, trigram in enumerate(circular_order, 1):
    print(f"{i}. {trigram.value}")
```

## 测试

运行完整的测试套件：

```bash
python run_tests.py
```

测试包括：
- ✅ 八卦到天干的映射测试
- ✅ 天干到八卦的映射测试
- ✅ 方位映射测试
- ✅ 符号映射测试
- ✅ 关系计算测试
- ✅ 数据一致性测试
- ✅ 性能测试

## 应用场景

### 🏛️ 传统文化研究
- 易经研究
- 风水学应用
- 奇门遁甲计算

### 💻 软件开发
- 日历系统
- 占卜应用
- 文化教育软件

### 📚 学术研究
- 古代天文学研究
- 中国哲学研究
- 文化传承项目

## 扩展功能

### 计划中的功能
- [ ] 地支映射支持
- [ ] 六十四卦扩展
- [ ] 时间计算功能
- [ ] 图形化界面
- [ ] Web API接口

### 贡献指南
欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 本系统基于传统八卦纳甲理论实现，仅供学习和研究使用。
