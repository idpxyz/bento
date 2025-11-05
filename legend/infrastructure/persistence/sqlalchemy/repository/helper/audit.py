from datetime import datetime
from idp.framework.shared.utils.date_time import utc_now

def fill_audit_fields(obj, actor: str):
    now = utc_now()
    if hasattr(obj, "updated_at"):
        obj.updated_at = now
    if hasattr(obj, "updated_by"):
        obj.updated_by = actor
# created_at/created_by 建议由 ORM default/oninsert 处理