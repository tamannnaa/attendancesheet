from datetime import date, timedelta

def date_range(start_date: date, end_date: date):
    dates = []
    d = start_date
    while d <= end_date:
        dates.append(d)
        d += timedelta(days=1)
    return dates


def is_weekend(check_date: date) -> bool:
    """Check if date is Saturday (5) or Sunday (6)"""
    return check_date.weekday() in [5, 6]


def is_holiday(check_date: date, holidays: list = None) -> bool:
    """Check if date is a holiday"""
    if holidays is None:
        holidays = []
    return check_date in holidays


def get_day_type(check_date: date, holidays: list = None) -> str:
    """
    Classify day type:
    - 'WEEKEND': Saturday or Sunday
    - 'HOLIDAY': In holiday list
    - 'WEEKDAY': Monday to Friday (non-holiday)
    """
    if is_holiday(check_date, holidays):
        return 'HOLIDAY'
    elif is_weekend(check_date):
        return 'WEEKEND'
    else:
        return 'WEEKDAY'


def get_day_of_week(check_date: date) -> str:
    """Get day name (Monday, Tuesday, etc.)"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[check_date.weekday()]