"""Change notifications for a publish that replaces an already-published parent version.
Delivery is a deliberate stub: this module decides WHO should be told and WHAT the
message says, and records that in ChangeNotification; actually sending an email/SMS is
left to a real adapter (swap `_deliver` for one, e.g. an SMTP or provider call) --
wiring up real credentials is outside this project's "no external dependencies without
configuration" scope."""
import logging

from sqlalchemy.orm import Session

from app.models.notification import ChangeNotification
from app.models.teacher import Teacher
from app.services.version_diff import diff_versions_by_occurrence

logger = logging.getLogger("timetable.notifications")


def _deliver(notification: ChangeNotification, teacher: Teacher | None) -> None:
    """Stub delivery: logs what WOULD be sent. Replace with a real adapter to actually
    email/SMS teachers; `notification.delivered` is left False until one exists."""
    target = teacher.email if teacher and teacher.email else "(no email on file)"
    logger.info("would notify %s: %s", target, notification.message)


def notify_publish_changes(db: Session, version_id: int, parent_version_id: int | None) -> int:
    """Diffs `version_id` against its parent (if any), occurrence-by-occurrence (not by
    subject/teacher alone, which collides whenever a pair meets more than once a week),
    and records one ChangeNotification per affected teacher and per affected section.
    Returns the number created."""
    if parent_version_id is None:
        return 0

    diffs = diff_versions_by_occurrence(db, parent_version_id, version_id)
    affected_teachers: set[int] = set()
    affected_sections: set[int] = set()
    for d in diffs:
        for side in (d.before, d.after):
            if side:
                if side["teacher_id"]:
                    affected_teachers.add(side["teacher_id"])
                affected_sections.update(side["section_ids"])

    created = 0
    for teacher_id in affected_teachers:
        teacher = db.get(Teacher, teacher_id)
        n = ChangeNotification(
            version_id=version_id, teacher_id=teacher_id,
            message=f"Your timetable changed in the newly published version (id {version_id}). "
                     "Check your schedule for updated sessions.",
        )
        db.add(n)
        _deliver(n, teacher)
        created += 1
    for section_id in affected_sections:
        n = ChangeNotification(
            version_id=version_id, section_id=section_id,
            message=f"This section's timetable changed in the newly published version (id {version_id}).",
        )
        db.add(n)
        _deliver(n, None)
        created += 1
    return created
