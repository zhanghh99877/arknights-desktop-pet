"""法定节假日表（2000-2099）：标红用。

- 农历节日（除夕/春节/端午/中秋）用 lunardate 换算，覆盖 1901-2099
- 清明用 21 世纪节气公式：day = int(y*0.2422 + 4.81) - int(y/4)，y = 年份后两位
- 固定日期：元旦 1.1、劳动节 5.1、国庆 10.1-10.3

用法：holidays.name_of(date(2026, 10, 1)) → "国庆节"，非节日返回 None。
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

try:
    from lunardate import LunarDate
except ImportError:  # 没装 lunardate 时退化为只标固定日期节日
    LunarDate = None

RANGE_START, RANGE_END = 2000, 2099


def _lunar(y: int, month: int, day: int) -> date:
    """农历转公历；腊月三十遇小月自动退回廿九。"""
    try:
        return LunarDate(y, month, day).to_solar_date()
    except ValueError:
        return LunarDate(y, month, day - 1).to_solar_date()


def _qingming(y: int) -> date:
    """清明日期（2000-2099 公式）。"""
    yy = y % 100
    return date(y, 4, int(yy * 0.2422 + 4.81) - int(yy / 4))


@lru_cache(maxsize=128)
def _year_table(y: int) -> dict[date, str]:
    """某年的全部法定节假日 {date: 名称}。除夕/春节优先，重名以先放入者为准。"""
    holidays: dict[date, str] = {
        date(y, 1, 1): "元旦",
        date(y, 5, 1): "劳动节",
        date(y, 10, 1): "国庆节",
        date(y, 10, 2): "国庆节",
        date(y, 10, 3): "国庆节",
        _qingming(y): "清明",
    }
    if LunarDate is not None:
        for d, name in (
            (_lunar(y - 1, 12, 30), "除夕"),   # 除夕常落在公历次年 1-2 月
            (_lunar(y, 1, 1), "春节"),
            (_lunar(y, 5, 5), "端午节"),
            (_lunar(y, 8, 15), "中秋节"),
        ):
            if RANGE_START <= d.year <= RANGE_END:
                holidays.setdefault(d, name)
    return holidays


def name_of(d: date) -> str | None:
    """某天的节日名，非节日 / 超出年份范围返回 None。"""
    if not (RANGE_START <= d.year <= RANGE_END):
        return None
    return _year_table(d.year).get(d)
