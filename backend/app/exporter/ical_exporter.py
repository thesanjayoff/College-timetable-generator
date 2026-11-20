from datetime import date, datetime, timedelta

from icalendar import Calendar, Event
from sqlalchemy.orm import Session

from app.exporter.common import get_default_structure, sessions_for_view


def export_ical(db: Session, version_id: int, term_start_date: date, term_weeks: int = 16,
                 teacher_id: int | None = None, section_id: int | None = None) -> bytes:
    """day_index 0 is assumed to be the Monday of `term_start_date`'s week."""
    structure = get_default_structure(db)
    periods_by_index = {p.period_index: p for p in structure.periods}
    sessions = sessions_for_view(db, version_id, section_id=section_id, teacher_id=teacher_id)

    monday = term_start_date - timedelta(days=term_start_date.weekday())

    cal = Calendar()
    cal.add("prodid", "-//College Timetable Generator//EN")
    cal.add("version", "2.0")

    for s in sessions:
        start_period = periods_by_index.get(s.period_index)
        end_period = periods_by_index.get(s.period_index + s.num_periods - 1)
        if start_period is None or end_period is None:
            continue
        event_date = monday + timedelta(days=s.day_index)
        sh, sm = map(int, start_period.start_time.split(":"))
        eh, em = map(int, end_period.end_time.split(":"))
        dtstart = datetime(event_date.year, event_date.month, event_date.day, sh, sm)
        dtend = datetime(event_date.year, event_date.month, event_date.day, eh, em)

        ev = Event()
        subject = s.subject.name if s.subject else "Class"
        ev.add("summary", subject)
        ev.add("dtstart", dtstart)
        ev.add("dtend", dtend)
        ev.add("rrule", {"freq": "weekly", "count": term_weeks})
        desc = []
        if s.teacher:
            desc.append(f"Teacher: {s.teacher.name}")
        if s.room:
            desc.append(f"Room: {s.room.code}")
        ev.add("description", "\n".join(desc))
        ev.add("uid", f"session-{s.id}@college-timetable")
        cal.add_component(ev)

    return cal.to_ical()
