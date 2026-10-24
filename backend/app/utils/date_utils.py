import calendar
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from typing import Optional, Any
from dateutil import parser as date_parser
from backend.app.core.config import settings

def get_tz() -> ZoneInfo:
    """Returns ZoneInfo instance for the configured timezone."""
    try:
        return ZoneInfo(settings.TIMEZONE)
    except Exception:
        return ZoneInfo("Asia/Kolkata")

def get_current_datetime() -> datetime:
    """Returns naive datetime representing current local time in configured timezone."""
    tz = get_tz()
    return datetime.now(tz).replace(tzinfo=None)

def add_calendar_months(dt: datetime, months: int) -> datetime:
    """
    Safely adds calendar months handling month-end transitions.
    e.g., 31st January + 1 month -> 28th/29th February.
    """
    year = dt.year
    month = dt.month + months
    
    # Calculate year overflow
    year_offset = (month - 1) // 12
    new_year = year + year_offset
    new_month = ((month - 1) % 12) + 1
    
    # Find max days in target month
    max_days = calendar.monthrange(new_year, new_month)[1]
    new_day = min(dt.day, max_days)
    
    return dt.replace(year=new_year, month=new_month, day=new_day)

def parse_flexible_date(val: Any) -> Optional[datetime]:
    """
    Parses dates from various formats (string, Excel serial float/int, datetime, date).
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, time.min)

    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", "-", "nat"]:
        return None

    # Try dateutil parser
    try:
        # Handles dayfirst=True commonly used in India (DD/MM/YYYY)
        return date_parser.parse(val_str, dayfirst=True)
    except Exception:
        pass

    # Try ISO format
    try:
        return datetime.fromisoformat(val_str)
    except Exception:
        return None
