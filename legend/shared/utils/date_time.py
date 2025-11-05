# 时区， 时区转换， 时间格式化，日期序列化

import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# 时区
TIMEZONE = 'Asia/Shanghai'

# 获取当前时间
def now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))

# 转换为本地时间
def to_local_time(dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo(TIMEZONE))

# 转换为UTC时间
def to_utc_time(dt: datetime) -> datetime:
    return dt.astimezone(ZoneInfo('UTC'))

# 格式化时间
def format_datetime(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
    return dt.strftime(fmt)

# 解析时间
def parse_datetime(dt_str: str, fmt: str = '%Y-%m-%d %H:%M:%S') -> datetime:
    return datetime.strptime(dt_str, fmt)

# 序列化时间
def serialize_datetime(dt: datetime) -> str:
    return dt.isoformat()

# 反序列化时间
def deserialize_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)

# 添加天数
def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)

# 添加小时
def add_hours(dt: datetime, hours: int) -> datetime:
    return dt + timedelta(hours=hours)

# 添加分钟
def add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)

# 添加秒
def add_seconds(dt: datetime, seconds: int) -> datetime:
    return dt + timedelta(seconds=seconds)

# 添加毫秒
def add_milliseconds(dt: datetime, milliseconds: int) -> datetime:
    return dt + timedelta(milliseconds=milliseconds)

# 添加微秒
def add_microseconds(dt: datetime, microseconds: int) -> datetime:
    return dt + timedelta(microseconds=microseconds)

# 添加周
def add_weeks(dt: datetime, weeks: int) -> datetime:
    return dt + timedelta(weeks=weeks)

# 添加月
def add_months(dt: datetime, months: int) -> datetime:
    return dt + timedelta(days=30 * months)

# 添加年
def add_years(dt: datetime, years: int) -> datetime:
    return dt + timedelta(days=365 * years)

# 减去天数
def subtract_days(dt: datetime, days: int) -> datetime:
    return dt - timedelta(days=days)

# 减去小时
def subtract_hours(dt: datetime, hours: int) -> datetime:
    return dt - timedelta(hours=hours)

# 减去分钟
def subtract_minutes(dt: datetime, minutes: int) -> datetime:
    return dt - timedelta(minutes=minutes)

# 减去秒
def subtract_seconds(dt: datetime, seconds: int) -> datetime:
    return dt - timedelta(seconds=seconds)

# 减去毫秒
def subtract_milliseconds(dt: datetime, milliseconds: int) -> datetime:
    return dt - timedelta(milliseconds=milliseconds)

# 减去微秒
def subtract_microseconds(dt: datetime, microseconds: int) -> datetime:
    return dt - timedelta(microseconds=microseconds)

# 减去周
def subtract_weeks(dt: datetime, weeks: int) -> datetime:
    return dt - timedelta(weeks=weeks)

# 减去月
def subtract_months(dt: datetime, months: int) -> datetime:
    return dt - timedelta(days=30 * months)

# 减去年
def subtract_years(dt: datetime, years: int) -> datetime:
    return dt - timedelta(days=365 * years)

# 判断是否是闰年
def is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

# 获取月份的第一天
def get_first_day_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1)

# 获取月份的最后一天
def get_last_day_of_month(dt: datetime) -> datetime:
    return (dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

# 获取年份的第一天
def get_first_day_of_year(dt: datetime) -> datetime:
    return dt.replace(month=1, day=1)

# 获取年份的最后一天
def get_last_day_of_year(dt: datetime) -> datetime:
    return dt.replace(month=12, day=31)

# 获取季度
def get_quarter(dt: datetime) -> int:
    return (dt.month - 1) // 3 + 1

# 获取月份的天数
def get_days_in_month(dt: datetime) -> int:
    return calendar.monthrange(dt.year, dt.month)[1]

# 获取年份的天数
def get_days_in_year(dt: datetime) -> int:
    return 366 if is_leap_year(dt.year) else 365

# 获取季度天数
def get_days_in_quarter(dt: datetime) -> int:
    return 92 + is_leap_year(dt.year)

def time_diff(dt1: datetime, dt2: datetime) -> int:
    return (dt1 - dt2).total_seconds()

def time_diff_in_seconds(dt1: datetime, dt2: datetime) -> int:
    return (dt1 - dt2).total_seconds()

def time_diff_in_minutes(dt1: datetime, dt2: datetime) -> int:
    return (dt1 - dt2).total_seconds() / 60

def time_diff_in_hours(dt1: datetime, dt2: datetime) -> int:
    return (dt1 - dt2).total_seconds() / 3600

def day_diff(dt1: datetime, dt2: datetime) -> int:
    return (dt1 - dt2).days

def month_diff(dt1: datetime, dt2: datetime) -> int:
    return (dt1.year - dt2.year) * 12 + dt1.month - dt2.month

def year_diff(dt1: datetime, dt2: datetime) -> int:
    return dt1.year - dt2.year

def quarter_diff(dt1: datetime, dt2: datetime) -> int:
    return (dt1.year - dt2.year) * 4 + (dt1.quarter - dt2.quarter)

def week_diff(dt1: datetime, dt2: datetime) -> int:
    return (dt1.year - dt2.year) * 52 + dt1.week - dt2.week

def timestamp_diff(dt1: datetime, dt2: datetime) -> int:
    return int((dt1 - datetime(1970, 1, 1)).total_seconds())

def timestamp_to_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp)

def datetime_to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp())

def utc_now() -> datetime:
    """获取当前 UTC 时间（带时区信息）
    
    Returns:
        datetime: 带 UTC 时区信息的当前时间
    """
    return datetime.now(timezone.utc)



