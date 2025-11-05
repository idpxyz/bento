import logging

from apscheduler.scheuvdulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger



# 基于 APScheduler 的 @cron 装饰器，实现定时任务注册。
# 使用方法：
# 1. 在需要定时执行的函数上添加 @cron(cron_expr) 装饰器
# 2. 装饰器会自动将函数注册为 APScheduler 的 Cron 任务
# 3. 任务会根据 cron_expr 指定的表达式定时执行
# 4. 任务的执行结果会通过 logging 记录


_scheduler = AsyncIOScheduler()
_scheduler.start()


def cron(cron_expr: str):
    """
    装饰器：将函数注册为 APScheduler 的 Cron 任务。
    expr 示例："*/5 * * * *"（每 5 分钟）
    """
    def decorator(fn):
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
            _scheduler.add_job(fn, trigger)
            logging.info(f"Scheduled job {fn.__name__} with cron '{cron_expr}'")
        except Exception as e:
            logging.error(f"Failed to schedule job {fn.__name__}: {e}")
        return fn
    return decorator