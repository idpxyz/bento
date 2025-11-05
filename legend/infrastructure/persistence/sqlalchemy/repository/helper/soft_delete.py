from idp.framework.shared.utils.date_time import utc_now


def mark_soft_deleted(obj, actor: str):
    """打软删标记 & 填充删除人/时间（如果字段存在）"""
    if hasattr(obj, "deleted_at"):
        obj.deleted_at = utc_now()
    if hasattr(obj, "deleted_by"):
        obj.deleted_by = actor