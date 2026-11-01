from __future__ import annotations

from datetime import date, datetime, time, timedelta


def get_next_slots(recruiter_id: int | str, count: int = 3, duration_minutes: int = 60) -> list[dict[str, str]]:
    start = datetime.utcnow().replace(second=0, microsecond=0)
    slots: list[dict[str, str]] = []
    busy = [
        (datetime(2026, 11, 3, 10, 0), datetime(2026, 11, 3, 11, 0)),
        (datetime(2026, 11, 4, 14, 0), datetime(2026, 11, 4, 15, 0)),
    ]

    current = max(start, datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0))
    day_cursor = current.date()
    while len(slots) < count:
        if day_cursor.weekday() < 5:
            slot_start = datetime.combine(day_cursor, time(9, 0))
            while slot_start + timedelta(minutes=duration_minutes) <= datetime.combine(day_cursor, time(17, 0)):
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                overlap = any(
                    slot_start < busy_end and slot_end > busy_start
                    for busy_start, busy_end in busy
                    if busy_start.date() == day_cursor
                )
                if not overlap and slot_start >= current:
                    slots.append({'start': slot_start.isoformat(), 'end': slot_end.isoformat()})
                    if len(slots) >= count:
                        break
                slot_start += timedelta(minutes=30)
        day_cursor += timedelta(days=1)
    return slots[:count]
