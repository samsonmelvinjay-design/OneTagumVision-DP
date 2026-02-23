"""
Working days (business days) for timeline calculations.
Excludes weekends (Saturday, Sunday) and Philippine holidays.
Uses official list for government employees (Regular + Special Non-Working Days).
"""
from datetime import date, timedelta


def _is_weekend(d):
    """Return True if d is Saturday (5) or Sunday (6)."""
    return d.weekday() >= 5


# Official Philippine holidays for government employees (Regular + Special Non-Working).
# Proclamation No. 1006, s. 2025. Islamic holidays (Eid'l Fitr, Eid'l Adha) are tentative and
# are typically not deducted from standardized working-day counts until dates are confirmed.
PH_HOLIDAYS_BY_YEAR = {
    2026: [
        # 2026 Regular Holidays (Eid'l Fitr Apr 1 and Eid'l Adha Jun 6 omitted for standardized count)
        date(2026, 1, 1),   # New Year's Day
        date(2026, 4, 2),   # Maundy Thursday
        date(2026, 4, 3),   # Good Friday
        date(2026, 4, 9),   # Araw ng Kagitingan (Day of Valor)
        date(2026, 5, 1),   # Labor Day
        date(2026, 6, 12),  # Independence Day
        date(2026, 8, 31),  # National Heroes Day
        date(2026, 11, 30), # Bonifacio Day
        date(2026, 12, 25), # Christmas Day
        date(2026, 12, 30), # Rizal Day
        # 2026 Special (Non-Working) Days
        date(2026, 2, 17),  # Chinese New Year
        date(2026, 4, 4),   # Black Saturday
        date(2026, 5, 12),  # National Election Day
        date(2026, 8, 21),  # Ninoy Aquino Day
        date(2026, 10, 31), # All Souls' Day (Special Non-Working)
        date(2026, 11, 1),  # All Saints' Day
        date(2026, 11, 2),  # All Souls' Day (Additional Special Day)
        date(2026, 12, 8),  # Feast of the Immaculate Conception
        date(2026, 12, 24), # Christmas Eve
        date(2026, 12, 31), # Last Day of the Year
    ],
}


def _get_ph_holidays_for_range(start_date, end_date):
    """Return a set of Philippine holiday dates between start_date and end_date (inclusive)."""
    out = set()
    for year in range(start_date.year, end_date.year + 1):
        if year in PH_HOLIDAYS_BY_YEAR:
            for d in PH_HOLIDAYS_BY_YEAR[year]:
                if start_date <= d <= end_date:
                    out.add(d)
        else:
            # Fallback: use python-holidays for years not in our list (optional dependency)
            try:
                import holidays
                ph = holidays.country_holidays('PH', years=[year])
                for d in ph:
                    if start_date <= d <= end_date:
                        out.add(d)
            except Exception:
                pass
    return out


def working_days_between(start_date, end_date):
    """
    Count working days between start_date and end_date (inclusive).
    Excludes weekends (Sat/Sun) and Philippine holidays (official list for government employees).

    Args:
        start_date: date
        end_date: date

    Returns:
        int: number of working days in [start_date, end_date].
             Returns 0 if end_date < start_date.
    """
    if not start_date or not end_date or end_date < start_date:
        return 0
    holidays_set = _get_ph_holidays_for_range(start_date, end_date)
    count = 0
    current = start_date
    while current <= end_date:
        if not _is_weekend(current) and current not in holidays_set:
            count += 1
        current += timedelta(days=1)
    return count
