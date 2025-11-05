from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.util import was_deleted


def has_entity_changed(new_obj, cur_obj, mapper: Mapper, *, skip=None) -> bool:
    """比较持久化前后字段是否变化，忽略版本/审计列"""
    # 默认跳过所有审计字段和技术字段
    skip = set(skip or {
        "version", "created_at", "updated_at", "created_by", "updated_by",
        "deleted_at", "deleted_by"
    })

    # 检查列字段的变化
    for col in mapper.columns:
        if col.key in skip:
            continue

        # 处理聚合对象可能没有某些PO字段的情况
        if not hasattr(new_obj, col.key):
            continue

        if getattr(new_obj, col.key) != getattr(cur_obj, col.key):
            return True

    # 检查关系字段的变化（避免触发延迟加载）
    for rel in mapper.relationships:
        rel_key = rel.key

        # 处理聚合对象可能没有某些关系字段的情况
        if not hasattr(new_obj, rel_key):
            continue

        new_rel_value = getattr(new_obj, rel_key)

        # 使用 inspect 检查当前对象的关系状态，避免触发延迟加载
        cur_obj_state = inspect(cur_obj)

        # 检查关系是否已加载
        if rel_key in cur_obj_state.unloaded:
            # 如果关系未加载，但新对象有数据，说明有变化
            if new_rel_value and (hasattr(new_rel_value, '__len__') and len(new_rel_value) > 0):
                return True
            continue

        cur_rel_value = getattr(cur_obj, rel_key)

        # 对于集合类型的关系，只比较长度（避免完整比较）
        if hasattr(new_rel_value, '__len__') and hasattr(cur_rel_value, '__len__'):
            if len(new_rel_value) != len(cur_rel_value):
                return True
        # 对于单个对象的关系，检查是否都为None或都不为None
        elif (new_rel_value is None) != (cur_rel_value is None):
            return True

    return False
