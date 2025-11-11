# BaseMapper 替换分析

## 兼容性检查结果

### ✅ 完全兼容的部分

1. **构造函数**
   - `base.py`: `__init__(domain_type, po_type)`
   - `base_new.py`: `__init__(domain_type, po_type, *, default_id_type=ID, ...)`
   - ✅ **兼容**：所有新参数都是可选的关键字参数

2. **大部分方法**
   - `register_child()` - ✅ 兼容（新增可选参数）
   - `convert_id_to_str()` - ✅ 完全一致
   - `convert_enum_to_str()` - ✅ 完全一致
   - `convert_str_to_enum()` - ✅ 完全一致（错误信息增强）
   - `map_reverse_children()` - ✅ 完全一致
   - `auto_clear_events()` - ✅ 完全一致
   - `get_child_mapper()` - ✅ 完全一致

### ⚠️ 需要检查的部分

1. **`convert_str_to_id()`**
   - `base.py`: `id_type: type = ID` (默认值 ID)
   - `base_new.py`: `id_type: type | None = None` (默认值 None，但使用 `default_id_type=ID`)
   - **实际行为**: ✅ 兼容（因为 `default_id_type` 默认是 `ID`）
   - **但**: 如果调用时不传 `id_type`，base_new.py 会先检查 `id_factory`，然后使用 `default_id_type`

2. **`map_children()`**
   - `base.py`: `set_parent_key: bool = True` (位置参数)
   - `base_new.py`: `*, set_parent_keys: bool = True` (关键字参数，参数名不同)
   - **实际使用**: 现有代码都使用默认值，不传第四个参数
   - **结论**: ✅ 兼容（因为都是默认值，且参数名变化不影响位置参数调用）

### ✅ 实际使用检查

从代码库检查结果：
- `map_children()` 调用都是：`self.map_children(domain, po, "items")` - 使用默认值
- `convert_str_to_id()` 调用：`self.convert_str_to_id(po.id, id_type=EntityId)` - 显式传参

**结论**: 现有代码使用方式完全兼容！

## 替换方案

### 方案 1: 直接替换（推荐）✅

**优点**:
- 简单直接
- base_new.py 功能更强大
- 向后兼容现有代码

**步骤**:
1. 备份 base.py
2. 将 base_new.py 内容复制到 base.py
3. 删除 base_new.py
4. 运行测试验证

### 方案 2: 添加兼容层

如果需要保持 100% API 兼容，可以在 base_new.py 中添加：
- `set_parent_key` 参数别名（已废弃，但保留兼容）

## 建议

**推荐使用方案 1（直接替换）**，因为：
1. ✅ 现有代码完全兼容
2. ✅ base_new.py 功能更强大
3. ✅ 代码更简洁（245 行 vs 292 行）
4. ✅ 支持更多场景（多租户、自定义 ID 等）

## 替换后的优势

1. **多外键支持** - 支持复杂层级关系
2. **映射上下文** - 自动传播 tenant_id, org_id 等
3. **自定义 ID 类型** - 支持强类型 ID（OrderId, CustomerId）
4. **批量方法** - map_list(), map_reverse_list()
5. **模板方法** - map_reverse_with_events() 确保事件清理
6. **更好的错误信息** - Enum 转换错误更详细

## 风险评估

- **低风险**: 现有代码使用方式完全兼容
- **测试建议**: 运行现有测试确保无回归

