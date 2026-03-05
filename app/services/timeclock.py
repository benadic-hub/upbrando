from __future__ import annotations

import datetime as dt

from app.db.models import BreakKind, TimeBreakWindow, TimeEntry, User


def _minutes_between(start: dt.datetime, end: dt.datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def _scheduled_work_minutes(user: User) -> int:
    start = dt.datetime.combine(dt.date.today(), user.work_start_time, tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(dt.date.today(), user.work_end_time, tzinfo=dt.timezone.utc)
    if end <= start:
        end += dt.timedelta(days=1)
    return _minutes_between(start, end) - int(user.break_minutes) - int(user.lunch_minutes)


def summarize_entry(*, user: User, entry: TimeEntry, windows: list[TimeBreakWindow]) -> tuple[int, int, int, int]:
    """Returns (worked, ot, break_minutes, lunch_minutes)."""
    if not entry.check_in_at or not entry.check_out_at:
        return 0, 0, 0, 0

    break_minutes = 0
    lunch_minutes = 0
    for window in windows:
        if not window.end_at:
            continue
        mins = _minutes_between(window.start_at, window.end_at)
        if window.kind == BreakKind.BREAK:
            break_minutes += mins
        elif window.kind == BreakKind.LUNCH:
            lunch_minutes += mins

    if break_minutes == 0:
        break_minutes = int(user.break_minutes)
    if lunch_minutes == 0:
        lunch_minutes = int(user.lunch_minutes)

    span_minutes = _minutes_between(entry.check_in_at, entry.check_out_at)
    worked_minutes = max(0, span_minutes - break_minutes - lunch_minutes)

    six_pm = dt.datetime.combine(entry.work_date, dt.time(hour=18), tzinfo=entry.check_out_at.tzinfo)
    over_six_pm = _minutes_between(six_pm, entry.check_out_at) if entry.check_out_at > six_pm else 0
    beyond_schedule = max(0, worked_minutes - _scheduled_work_minutes(user))
    ot_minutes = max(over_six_pm, beyond_schedule)

    return worked_minutes, ot_minutes, break_minutes, lunch_minutes

