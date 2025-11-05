"""数据库上下文变量"""

import contextvars

# 事务上下文变量，用于追踪当前是否在事务中
in_transaction = contextvars.ContextVar('in_transaction', default=False)

# 数据库请求追踪ID
request_id = contextvars.ContextVar('request_id', default=None)

# 当前会话ID
session_id = contextvars.ContextVar('session_id', default=None) 