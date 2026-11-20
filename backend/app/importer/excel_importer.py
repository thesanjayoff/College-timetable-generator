"""Excel bulk importer. Validates every sheet first and reports precise (sheet, row,
column) errors; only writes to the database if the whole workbook is clean."""
import io
from dataclasses import dataclass, field

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.college import Department, LabBatch, Program, Section
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.enums import PeriodKind, PreferenceType, RoomType, SubjectType
from app.models.room import Room
from app.models.structure import PeriodSlot, TimeStructure, WorkingDay
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherPreference, TeacherSubject, TeacherUnavailability


@dataclass
class ImportError_:
    sheet: str
    row: int  # 1-based, matching the Excel row number (header is row 1)
    column: str
    message: str


@dataclass
class ImportReport:
    errors: list[ImportError_] = field(default_factory=list)
    created_counts: dict[str, int] = field(default_factory=dict)
    committed: bool = False

    def to_dict(self) -> dict:
        return {
            "committed": self.committed,
            "created_counts": self.created_counts,
            "errors": [{"sheet": e.sheet, "row": e.row, "column": e.column, "message": e.message}
                       for e in self.errors],
        }


def _read_sheet(wb, name: str) -> list[dict]:
    if name not in wb.sheetnames:
        return []
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for i, row in enumerate(rows[1:], start=2):
        if all(v is None for v in row):
            continue
        record = {headers[ci]: row[ci] for ci in range(len(headers)) if ci < len(row)}
        record["__row__"] = i
        out.append(record)
    return out


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("yes", "true", "1", "y") if v is not None else False


class _Importer:
    def __init__(self, db: Session):
        self.db = db
        self.report = ImportReport()
        self.dept_by_code: dict[str, Department] = {}
        self.program_by_code: dict[str, Program] = {}
        self.section_by_key: dict[tuple, Section] = {}
        self.batch_by_key: dict[tuple, LabBatch] = {}
        self.subject_by_code: dict[str, Subject] = {}
        self.teacher_by_code: dict[str, Teacher] = {}
        self.room_by_code: dict[str, Room] = {}
        self.structure_by_name: dict[str, TimeStructure] = {}
        self.basket_by_name: dict[str, ElectiveBasket] = {}
        self.combined_by_name: dict[str, CombinedClass] = {}

    def err(self, sheet, row, column, message):
        self.report.errors.append(ImportError_(sheet, row, column, message))

    def count(self, key):
        self.report.created_counts[key] = self.report.created_counts.get(key, 0) + 1

    # -------------------------------------------------------------- sheets
    def departments(self, rows):
        for r in rows:
            code = (r.get("code") or "").strip()
            name = (r.get("name") or "").strip()
            if not code:
                self.err("Departments", r["__row__"], "code", "code is required")
                continue
            if not name:
                self.err("Departments", r["__row__"], "name", "name is required")
                continue
            existing = self.db.query(Department).filter(Department.code == code).first()
            if existing:
                existing.name = name
                self.dept_by_code[code] = existing
            else:
                d = Department(code=code, name=name)
                self.db.add(d)
                self.db.flush()
                self.dept_by_code[code] = d
                self.count("departments")

    def programs(self, rows):
        for r in rows:
            code = (r.get("code") or "").strip()
            dept_code = (r.get("department_code") or "").strip()
            if not code:
                self.err("Programs", r["__row__"], "code", "code is required")
                continue
            dept = self.dept_by_code.get(dept_code)
            if dept is None:
                self.err("Programs", r["__row__"], "department_code", f"Unknown department '{dept_code}'")
                continue
            existing = self.db.query(Program).filter(Program.code == code).first()
            duration = int(r.get("duration_semesters") or 8)
            if existing:
                existing.name, existing.department_id, existing.duration_semesters = r.get("name"), dept.id, duration
                self.program_by_code[code] = existing
            else:
                p = Program(code=code, name=r.get("name") or code, department_id=dept.id,
                            duration_semesters=duration)
                self.db.add(p)
                self.db.flush()
                self.program_by_code[code] = p
                self.count("programs")

    def time_structures(self, rows):
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                self.err("TimeStructures", r["__row__"], "name", "name is required")
                continue
            existing = self.db.query(TimeStructure).filter(TimeStructure.name == name).first()
            if existing:
                existing.is_default = _truthy(r.get("is_default"))
                self.structure_by_name[name] = existing
            else:
                s = TimeStructure(name=name, is_default=_truthy(r.get("is_default")))
                self.db.add(s)
                self.db.flush()
                self.structure_by_name[name] = s
                self.count("time_structures")

    def working_days(self, rows):
        for r in rows:
            sname = (r.get("structure_name") or "").strip()
            structure = self.structure_by_name.get(sname)
            if structure is None:
                self.err("WorkingDays", r["__row__"], "structure_name", f"Unknown structure '{sname}'")
                continue
            try:
                day_index = int(r.get("day_index"))
            except (TypeError, ValueError):
                self.err("WorkingDays", r["__row__"], "day_index", "must be an integer")
                continue
            max_p = r.get("max_period_index")
            max_p = int(max_p) if max_p not in (None, "") else None
            existing = self.db.query(WorkingDay).filter(
                WorkingDay.time_structure_id == structure.id, WorkingDay.day_index == day_index
            ).first()
            if existing:
                existing.name, existing.max_period_index = r.get("name") or existing.name, max_p
            else:
                self.db.add(WorkingDay(time_structure_id=structure.id, day_index=day_index,
                                        name=r.get("name") or f"Day {day_index}", max_period_index=max_p))
                self.count("working_days")

    def period_slots(self, rows):
        for r in rows:
            sname = (r.get("structure_name") or "").strip()
            structure = self.structure_by_name.get(sname)
            if structure is None:
                self.err("PeriodSlots", r["__row__"], "structure_name", f"Unknown structure '{sname}'")
                continue
            try:
                period_index = int(r.get("period_index"))
            except (TypeError, ValueError):
                self.err("PeriodSlots", r["__row__"], "period_index", "must be an integer")
                continue
            kind = (r.get("kind") or "teaching").strip().lower()
            if kind not in (k.value for k in PeriodKind):
                self.err("PeriodSlots", r["__row__"], "kind", f"must be one of teaching/break/lunch, got '{kind}'")
                continue
            existing = self.db.query(PeriodSlot).filter(
                PeriodSlot.time_structure_id == structure.id, PeriodSlot.period_index == period_index
            ).first()
            vals = dict(label=r.get("label") or f"P{period_index}", start_time=str(r.get("start_time") or ""),
                        end_time=str(r.get("end_time") or ""), kind=PeriodKind(kind))
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
            else:
                self.db.add(PeriodSlot(time_structure_id=structure.id, period_index=period_index, **vals))
                self.count("period_slots")

    def sections(self, rows):
        for r in rows:
            pcode = (r.get("program_code") or "").strip()
            program = self.program_by_code.get(pcode)
            if program is None:
                self.err("Sections", r["__row__"], "program_code", f"Unknown program '{pcode}'")
                continue
            try:
                sem = int(r.get("semester_number"))
            except (TypeError, ValueError):
                self.err("Sections", r["__row__"], "semester_number", "must be an integer")
                continue
            name = (r.get("name") or "").strip()
            if not name:
                self.err("Sections", r["__row__"], "name", "name is required")
                continue
            strength = int(r.get("strength") or 60)
            key = (pcode, sem, name)
            existing = self.db.query(Section).filter(
                Section.program_id == program.id, Section.semester_number == sem, Section.name == name
            ).first()
            if existing:
                existing.strength = strength
                self.section_by_key[key] = existing
            else:
                s = Section(program_id=program.id, semester_number=sem, name=name, strength=strength)
                self.db.add(s)
                self.db.flush()
                self.section_by_key[key] = s
                self.count("sections")

    def lab_batches(self, rows):
        for r in rows:
            key = ((r.get("program_code") or "").strip(), self._int_or_none(r.get("semester_number")),
                   (r.get("section_name") or "").strip())
            section = self.section_by_key.get(key)
            if section is None:
                self.err("LabBatches", r["__row__"], "section_name", f"Unknown section for {key}")
                continue
            bname = (r.get("batch_name") or "").strip()
            if not bname:
                self.err("LabBatches", r["__row__"], "batch_name", "batch_name is required")
                continue
            strength = int(r.get("strength") or 30)
            bkey = key + (bname,)
            existing = self.db.query(LabBatch).filter(
                LabBatch.section_id == section.id, LabBatch.name == bname
            ).first()
            if existing:
                existing.strength = strength
                self.batch_by_key[bkey] = existing
            else:
                b = LabBatch(section_id=section.id, name=bname, strength=strength)
                self.db.add(b)
                self.db.flush()
                self.batch_by_key[bkey] = b
                self.count("lab_batches")

    def subjects(self, rows):
        for r in rows:
            code = (r.get("code") or "").strip()
            dept = self.dept_by_code.get((r.get("department_code") or "").strip())
            if not code:
                self.err("Subjects", r["__row__"], "code", "code is required")
                continue
            if dept is None:
                self.err("Subjects", r["__row__"], "department_code", "Unknown department")
                continue
            stype = (r.get("subject_type") or "").strip().lower()
            if stype not in (t.value for t in SubjectType):
                self.err("Subjects", r["__row__"], "subject_type", f"Invalid subject_type '{stype}'")
                continue
            vals = dict(
                name=r.get("name") or code, department_id=dept.id, subject_type=SubjectType(stype),
                credits=float(r.get("credits") or 3), periods_per_week=int(r.get("periods_per_week") or 3),
                sessions_per_week=int(r.get("sessions_per_week") or 3), block_size=int(r.get("block_size") or 1),
                spread_across_days=_truthy(r.get("spread_across_days")), max_per_day=int(r.get("max_per_day") or 1),
                requires_lab_batches=_truthy(r.get("requires_lab_batches")),
                avoid_last_period=_truthy(r.get("avoid_last_period")), prefer_afternoon=_truthy(r.get("prefer_afternoon")),
            )
            existing = self.db.query(Subject).filter(Subject.code == code).first()
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                self.subject_by_code[code] = existing
            else:
                s = Subject(code=code, **vals)
                self.db.add(s)
                self.db.flush()
                self.subject_by_code[code] = s
                self.count("subjects")

    def teachers(self, rows):
        for r in rows:
            code = (r.get("code") or "").strip()
            dept = self.dept_by_code.get((r.get("department_code") or "").strip())
            if not code:
                self.err("Teachers", r["__row__"], "code", "code is required")
                continue
            if dept is None:
                self.err("Teachers", r["__row__"], "department_code", "Unknown department")
                continue
            visiting_days_raw = r.get("visiting_days")
            visiting_days = None
            if visiting_days_raw:
                try:
                    visiting_days = [int(x.strip()) for x in str(visiting_days_raw).split(",") if x.strip()]
                except ValueError:
                    self.err("Teachers", r["__row__"], "visiting_days", "must be comma-separated integers")
                    continue
            vals = dict(
                name=r.get("name") or code, department_id=dept.id, email=r.get("email"),
                max_periods_per_day=int(r.get("max_periods_per_day") or 6),
                max_periods_per_week=int(r.get("max_periods_per_week") or 24),
                max_consecutive_periods=int(r.get("max_consecutive_periods") or 4),
                is_visiting=_truthy(r.get("is_visiting")), visiting_days=visiting_days,
            )
            existing = self.db.query(Teacher).filter(Teacher.code == code).first()
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                self.teacher_by_code[code] = existing
            else:
                t = Teacher(code=code, **vals)
                self.db.add(t)
                self.db.flush()
                self.teacher_by_code[code] = t
                self.count("teachers")

    def teacher_subjects(self, rows):
        for r in rows:
            t = self.teacher_by_code.get((r.get("teacher_code") or "").strip())
            s = self.subject_by_code.get((r.get("subject_code") or "").strip())
            if t is None:
                self.err("TeacherSubjects", r["__row__"], "teacher_code", "Unknown teacher")
                continue
            if s is None:
                self.err("TeacherSubjects", r["__row__"], "subject_code", "Unknown subject")
                continue
            existing = self.db.query(TeacherSubject).filter(
                TeacherSubject.teacher_id == t.id, TeacherSubject.subject_id == s.id
            ).first()
            if not existing:
                self.db.add(TeacherSubject(teacher_id=t.id, subject_id=s.id))
                self.count("teacher_subjects")

    def teacher_unavailability(self, rows):
        for r in rows:
            t = self.teacher_by_code.get((r.get("teacher_code") or "").strip())
            if t is None:
                self.err("TeacherUnavailability", r["__row__"], "teacher_code", "Unknown teacher")
                continue
            try:
                day_index = int(r.get("day_index"))
            except (TypeError, ValueError):
                self.err("TeacherUnavailability", r["__row__"], "day_index", "must be an integer")
                continue
            pcol = "period_index_or_blank_for_whole_day"
            period_index = self._int_or_none(r.get(pcol))
            self.db.add(TeacherUnavailability(teacher_id=t.id, day_index=day_index, period_index=period_index))
            self.count("teacher_unavailability")

    def teacher_preferences(self, rows):
        for r in rows:
            t = self.teacher_by_code.get((r.get("teacher_code") or "").strip())
            if t is None:
                self.err("TeacherPreferences", r["__row__"], "teacher_code", "Unknown teacher")
                continue
            ptype = (r.get("preference_type") or "").strip().lower()
            if ptype not in (p.value for p in PreferenceType):
                self.err("TeacherPreferences", r["__row__"], "preference_type", f"Invalid '{ptype}'")
                continue
            self.db.add(TeacherPreference(
                teacher_id=t.id, preference_type=PreferenceType(ptype),
                day_index=self._int_or_none(r.get("day_index")), weight=float(r.get("weight") or 1.0),
            ))
            self.count("teacher_preferences")

    def rooms(self, rows):
        for r in rows:
            code = (r.get("code") or "").strip()
            rtype = (r.get("room_type") or "").strip().lower()
            if not code:
                self.err("Rooms", r["__row__"], "code", "code is required")
                continue
            if rtype not in (t.value for t in RoomType):
                self.err("Rooms", r["__row__"], "room_type", f"Invalid room_type '{rtype}'")
                continue
            vals = dict(
                name=r.get("name") or code, room_type=RoomType(rtype), capacity=int(r.get("capacity") or 60),
                lab_category=r.get("lab_category") or None, building=r.get("building") or None,
                floor=self._int_or_none(r.get("floor")),
            )
            existing = self.db.query(Room).filter(Room.code == code).first()
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                self.room_by_code[code] = existing
            else:
                room = Room(code=code, **vals)
                self.db.add(room)
                self.db.flush()
                self.room_by_code[code] = room
                self.count("rooms")

    def allocations(self, rows):
        for r in rows:
            subject = self.subject_by_code.get((r.get("subject_code") or "").strip())
            if subject is None:
                self.err("Allocations", r["__row__"], "subject_code", "Unknown subject")
                continue
            key = ((r.get("program_code") or "").strip(), self._int_or_none(r.get("semester_number")),
                   (r.get("section_name") or "").strip())
            section = self.section_by_key.get(key)
            if section is None:
                self.err("Allocations", r["__row__"], "section_name", f"Unknown section for {key}")
                continue
            batch_name = (r.get("batch_name_or_blank") or "").strip()
            batch = None
            if batch_name:
                batch = self.batch_by_key.get(key + (batch_name,))
                if batch is None:
                    self.err("Allocations", r["__row__"], "batch_name_or_blank", f"Unknown batch '{batch_name}'")
                    continue
            teacher_code = (r.get("teacher_code_or_blank") or "").strip()
            teacher = self.teacher_by_code.get(teacher_code) if teacher_code else None
            if teacher_code and teacher is None:
                self.err("Allocations", r["__row__"], "teacher_code_or_blank", f"Unknown teacher '{teacher_code}'")
                continue
            room_code = (r.get("room_code_or_blank") or "").strip()
            room = self.room_by_code.get(room_code) if room_code else None
            if room_code and room is None:
                self.err("Allocations", r["__row__"], "room_code_or_blank", f"Unknown room '{room_code}'")
                continue
            existing = self.db.query(Allocation).filter(
                Allocation.subject_id == subject.id, Allocation.section_id == section.id,
                Allocation.lab_batch_id == (batch.id if batch else None),
            ).first()
            if existing:
                existing.teacher_id = teacher.id if teacher else existing.teacher_id
                existing.is_fixed_teacher = teacher is not None
                existing.room_id = room.id if room else existing.room_id
                existing.is_fixed_room = room is not None
            else:
                self.db.add(Allocation(
                    subject_id=subject.id, section_id=section.id, lab_batch_id=batch.id if batch else None,
                    teacher_id=teacher.id if teacher else None, is_fixed_teacher=teacher is not None,
                    room_id=room.id if room else None, is_fixed_room=room is not None,
                ))
                self.count("allocations")

    def elective_baskets(self, rows):
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                self.err("ElectiveBaskets", r["__row__"], "name", "name is required")
                continue
            existing = self.db.query(ElectiveBasket).filter(ElectiveBasket.name == name).first()
            vals = dict(sessions_per_week=int(r.get("sessions_per_week") or 1), block_size=int(r.get("block_size") or 1))
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                self.basket_by_name[name] = existing
            else:
                b = ElectiveBasket(name=name, **vals)
                self.db.add(b)
                self.db.flush()
                self.basket_by_name[name] = b
                self.count("elective_baskets")

    def elective_options(self, rows):
        for r in rows:
            basket = self.basket_by_name.get((r.get("basket_name") or "").strip())
            subject = self.subject_by_code.get((r.get("subject_code") or "").strip())
            if basket is None:
                self.err("ElectiveOptions", r["__row__"], "basket_name", "Unknown basket")
                continue
            if subject is None:
                self.err("ElectiveOptions", r["__row__"], "subject_code", "Unknown subject")
                continue
            teacher_code = (r.get("teacher_code_or_blank") or "").strip()
            teacher = self.teacher_by_code.get(teacher_code) if teacher_code else None
            rtype = (r.get("room_type_required") or "classroom").strip().lower()
            if rtype not in (t.value for t in RoomType):
                self.err("ElectiveOptions", r["__row__"], "room_type_required", f"Invalid '{rtype}'")
                continue
            existing = self.db.query(ElectiveOption).filter(
                ElectiveOption.basket_id == basket.id, ElectiveOption.subject_id == subject.id
            ).first()
            vals = dict(teacher_id=teacher.id if teacher else None, room_type_required=RoomType(rtype),
                        expected_strength=int(r.get("expected_strength") or 30))
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
            else:
                self.db.add(ElectiveOption(basket_id=basket.id, subject_id=subject.id, **vals))
                self.count("elective_options")

    def elective_participations(self, rows):
        for r in rows:
            basket = self.basket_by_name.get((r.get("basket_name") or "").strip())
            key = ((r.get("program_code") or "").strip(), self._int_or_none(r.get("semester_number")),
                   (r.get("section_name") or "").strip())
            section = self.section_by_key.get(key)
            if basket is None:
                self.err("ElectiveParticipations", r["__row__"], "basket_name", "Unknown basket")
                continue
            if section is None:
                self.err("ElectiveParticipations", r["__row__"], "section_name", f"Unknown section for {key}")
                continue
            existing = self.db.query(ElectiveParticipation).filter(
                ElectiveParticipation.basket_id == basket.id, ElectiveParticipation.section_id == section.id
            ).first()
            if not existing:
                self.db.add(ElectiveParticipation(basket_id=basket.id, section_id=section.id))
                self.count("elective_participations")

    def combined_classes(self, rows):
        for r in rows:
            name = (r.get("name") or "").strip()
            subject = self.subject_by_code.get((r.get("subject_code") or "").strip())
            if not name:
                self.err("CombinedClasses", r["__row__"], "name", "name is required")
                continue
            if subject is None:
                self.err("CombinedClasses", r["__row__"], "subject_code", "Unknown subject")
                continue
            teacher_code = (r.get("teacher_code_or_blank") or "").strip()
            teacher = self.teacher_by_code.get(teacher_code) if teacher_code else None
            rtype = (r.get("room_type_required") or "seminar_hall").strip().lower()
            if rtype not in (t.value for t in RoomType):
                self.err("CombinedClasses", r["__row__"], "room_type_required", f"Invalid '{rtype}'")
                continue
            existing = self.db.query(CombinedClass).filter(CombinedClass.name == name).first()
            vals = dict(subject_id=subject.id, teacher_id=teacher.id if teacher else None,
                        sessions_per_week=int(r.get("sessions_per_week") or 1),
                        block_size=int(r.get("block_size") or 1), room_type_required=RoomType(rtype))
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                self.combined_by_name[name] = existing
            else:
                c = CombinedClass(name=name, **vals)
                self.db.add(c)
                self.db.flush()
                self.combined_by_name[name] = c
                self.count("combined_classes")

    def combined_class_sections(self, rows):
        for r in rows:
            cc = self.combined_by_name.get((r.get("combined_class_name") or "").strip())
            key = ((r.get("program_code") or "").strip(), self._int_or_none(r.get("semester_number")),
                   (r.get("section_name") or "").strip())
            section = self.section_by_key.get(key)
            if cc is None:
                self.err("CombinedClassSections", r["__row__"], "combined_class_name", "Unknown combined class")
                continue
            if section is None:
                self.err("CombinedClassSections", r["__row__"], "section_name", f"Unknown section for {key}")
                continue
            existing = self.db.query(CombinedClassSection).filter(
                CombinedClassSection.combined_class_id == cc.id, CombinedClassSection.section_id == section.id
            ).first()
            if not existing:
                self.db.add(CombinedClassSection(combined_class_id=cc.id, section_id=section.id))
                self.count("combined_class_sections")

    @staticmethod
    def _int_or_none(v):
        if v in (None, ""):
            return None
        return int(v)


def import_workbook(db: Session, file_bytes: bytes, dry_run: bool = False) -> ImportReport:
    wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
    importer = _Importer(db)

    pipeline = [
        ("Departments", importer.departments),
        ("Programs", importer.programs),
        ("TimeStructures", importer.time_structures),
        ("WorkingDays", importer.working_days),
        ("PeriodSlots", importer.period_slots),
        ("Sections", importer.sections),
        ("LabBatches", importer.lab_batches),
        ("Subjects", importer.subjects),
        ("Teachers", importer.teachers),
        ("TeacherSubjects", importer.teacher_subjects),
        ("TeacherUnavailability", importer.teacher_unavailability),
        ("TeacherPreferences", importer.teacher_preferences),
        ("Rooms", importer.rooms),
        ("Allocations", importer.allocations),
        ("ElectiveBaskets", importer.elective_baskets),
        ("ElectiveOptions", importer.elective_options),
        ("ElectiveParticipations", importer.elective_participations),
        ("CombinedClasses", importer.combined_classes),
        ("CombinedClassSections", importer.combined_class_sections),
    ]

    try:
        for sheet_name, handler in pipeline:
            rows = _read_sheet(wb, sheet_name)
            if rows:
                handler(rows)

        if importer.report.errors or dry_run:
            db.rollback()
        else:
            db.commit()
            importer.report.committed = True
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        importer.err("workbook", 0, "", f"Unexpected error: {exc}")

    return importer.report
