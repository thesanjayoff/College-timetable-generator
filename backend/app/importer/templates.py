"""Generates the Excel import templates: one workbook, one sheet per entity, with a
header row, a couple of example rows, and a Notes sheet explaining each column."""
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

HEADER_FILL = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)

SHEETS: dict[str, tuple[list[str], list[list]]] = {
    "Departments": (
        ["code", "name"],
        [["CSE", "Computer Science & Engineering"], ["ECE", "Electronics & Communication"]],
    ),
    "Programs": (
        ["code", "name", "department_code", "duration_semesters"],
        [["BTCSE", "B.Tech CSE", "CSE", 8]],
    ),
    "TimeStructures": (
        ["name", "is_default"],
        [["Default", "yes"]],
    ),
    "WorkingDays": (
        ["structure_name", "day_index", "name", "max_period_index"],
        [["Default", 0, "Monday", ""], ["Default", 5, "Saturday", 3]],
    ),
    "PeriodSlots": (
        ["structure_name", "period_index", "label", "start_time", "end_time", "kind"],
        [["Default", 0, "P1", "09:00", "09:50", "teaching"], ["Default", 4, "Lunch", "13:00", "13:40", "lunch"]],
    ),
    "Sections": (
        ["program_code", "semester_number", "name", "strength"],
        [["BTCSE", 3, "A", 60], ["BTCSE", 3, "B", 58]],
    ),
    "LabBatches": (
        ["program_code", "semester_number", "section_name", "batch_name", "strength"],
        [["BTCSE", 3, "A", "A1", 30], ["BTCSE", 3, "A", "A2", 30]],
    ),
    "Subjects": (
        ["code", "name", "department_code", "subject_type", "credits", "periods_per_week",
         "sessions_per_week", "block_size", "spread_across_days", "max_per_day",
         "requires_lab_batches", "avoid_last_period", "prefer_afternoon"],
        [["CS301", "Data Structures", "CSE", "theory", 3, 3, 3, 1, "yes", 1, "no", "no", "no"],
         ["CS301L", "DS Lab", "CSE", "lab", 2, 2, 1, 2, "yes", 1, "yes", "no", "yes"]],
    ),
    "Teachers": (
        ["code", "name", "department_code", "email", "max_periods_per_day", "max_periods_per_week",
         "max_consecutive_periods", "is_visiting", "visiting_days"],
        [["T001", "Dr. A. Rao", "CSE", "a.rao@example.edu", 6, 24, 4, "no", ""]],
    ),
    "TeacherSubjects": (
        ["teacher_code", "subject_code"],
        [["T001", "CS301"]],
    ),
    "TeacherUnavailability": (
        ["teacher_code", "day_index", "period_index_or_blank_for_whole_day"],
        [["T001", 5, ""]],
    ),
    "TeacherPreferences": (
        ["teacher_code", "preference_type", "day_index", "weight"],
        [["T001", "free_day", 5, 1.0]],
    ),
    "Rooms": (
        ["code", "name", "room_type", "capacity", "lab_category", "building", "floor"],
        [["C101", "Classroom 101", "classroom", 70, "", "Main Block", 1],
         ["L201", "Computer Lab 1", "lab", 35, "computer", "Lab Block", 2]],
    ),
    "Allocations": (
        ["subject_code", "program_code", "semester_number", "section_name", "batch_name_or_blank",
         "teacher_code_or_blank", "room_code_or_blank"],
        [["CS301", "BTCSE", 3, "A", "", "T001", ""],
         ["CS301L", "BTCSE", 3, "A", "A1", "T001", "L201"]],
    ),
    "ElectiveBaskets": (
        ["name", "sessions_per_week", "block_size"],
        [["Open Elective Basket 1", 3, 1]],
    ),
    "ElectiveOptions": (
        ["basket_name", "subject_code", "teacher_code_or_blank", "room_type_required", "expected_strength"],
        [["Open Elective Basket 1", "CS301", "", "classroom", 30]],
    ),
    "ElectiveParticipations": (
        ["basket_name", "program_code", "semester_number", "section_name"],
        [["Open Elective Basket 1", "BTCSE", 3, "A"]],
    ),
    "CombinedClasses": (
        ["name", "subject_code", "teacher_code_or_blank", "sessions_per_week", "block_size", "room_type_required"],
        [["Joint Lecture", "CS301", "", 1, 1, "seminar_hall"]],
    ),
    "CombinedClassSections": (
        ["combined_class_name", "program_code", "semester_number", "section_name"],
        [["Joint Lecture", "BTCSE", 3, "A"]],
    ),
}

NOTES = [
    ("Sheet", "Column", "Notes"),
    ("General", "", "Fill sheets top-to-bottom: Departments/Programs before Sections, etc. "
                     "Leave a cell blank rather than writing 'null' or 'N/A'."),
    ("Subjects", "subject_type", "One of: theory, lab, tutorial, project, library, sports, mentoring, "
                                  "open_elective, professional_elective"),
    ("Subjects", "block_size", "Consecutive periods per session (1 for theory, 2-3 for labs)."),
    ("Rooms", "room_type", "One of: classroom, lab, seminar_hall"),
    ("Allocations", "batch_name_or_blank", "Fill in only for lab subjects that require batches; one row per batch."),
    ("TeacherUnavailability", "period_index_or_blank_for_whole_day", "Blank means the teacher is unavailable "
                                                                     "the whole day."),
]


def _write_sheet(wb: Workbook, title: str, headers: list[str], examples: list[list]) -> Worksheet:
    ws = wb.create_sheet(title=title[:31])
    for ci, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
    for ri, row in enumerate(examples, start=2):
        for ci, val in enumerate(row, start=1):
            ws.cell(row=ri, column=ci, value=val)
    for ci in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = 22
    return ws


def generate_template_workbook() -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    notes_ws = wb.create_sheet(title="Notes")
    for ri, row in enumerate(NOTES, start=1):
        for ci, val in enumerate(row, start=1):
            cell = notes_ws.cell(row=ri, column=ci, value=val)
            if ri == 1:
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
    notes_ws.column_dimensions["A"].width = 20
    notes_ws.column_dimensions["B"].width = 20
    notes_ws.column_dimensions["C"].width = 70

    for name, (headers, examples) in SHEETS.items():
        _write_sheet(wb, name, headers, examples)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
