import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy.orm import Session

from app.exporter.common import cell_label, get_default_structure, sessions_for_view, structure_grid_labels

HEADER_FILL = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _build_grid_sheet(wb: Workbook, title: str, db: Session, version_id: int, college_name: str,
                       section_id=None, teacher_id=None, room_id=None):
    structure = get_default_structure(db)
    days, periods = structure_grid_labels(structure)
    sessions = sessions_for_view(db, version_id, section_id, teacher_id, room_id)

    ws = wb.create_sheet(title=title[:31])
    ws.cell(row=1, column=1, value=f"{college_name} - {title}").font = Font(bold=True, size=14)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(days) + 1)

    ws.cell(row=2, column=1, value="Period").fill = HEADER_FILL
    ws.cell(row=2, column=1).font = HEADER_FONT
    for ci, d in enumerate(days, start=2):
        c = ws.cell(row=2, column=ci, value=d.name)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center")

    by_slot = {}
    for s in sessions:
        by_slot.setdefault((s.day_index, s.period_index), []).append(s)

    row = 3
    for p in periods:
        if p.kind.value != "teaching":
            label = "Lunch" if p.kind.value == "lunch" else "Break"
            ws.cell(row=row, column=1, value=label).font = Font(italic=True)
        else:
            ws.cell(row=row, column=1, value=f"{p.label}\n{p.start_time}-{p.end_time}")
        for ci, d in enumerate(days, start=2):
            if p.kind.value != "teaching":
                continue
            if d.max_period_index is not None and p.period_index > d.max_period_index:
                ws.cell(row=row, column=ci, value="-")
                continue
            matches = by_slot.get((d.day_index, p.period_index), [])
            text = " / ".join(cell_label(m) for m in matches)
            cell = ws.cell(row=row, column=ci, value=text)
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        row += 1

    ws.column_dimensions["A"].width = 16
    for ci in range(2, len(days) + 2):
        ws.column_dimensions[ws.cell(row=2, column=ci).column_letter].width = 22
    return ws


def export_grid_excel(db: Session, version_id: int, title: str, college_name: str = "",
                       section_id=None, teacher_id=None, room_id=None) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    _build_grid_sheet(wb, title, db, version_id, college_name, section_id, teacher_id, room_id)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_all_sections_excel(db: Session, version_id: int, college_name: str = "") -> bytes:
    from app.models.college import Section
    wb = Workbook()
    wb.remove(wb.active)
    for sec in db.query(Section).all():
        _build_grid_sheet(wb, sec.display_name, db, version_id, college_name, section_id=sec.id)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_all_teachers_excel(db: Session, version_id: int, college_name: str = "") -> bytes:
    from app.models.teacher import Teacher
    wb = Workbook()
    wb.remove(wb.active)
    for t in db.query(Teacher).all():
        _build_grid_sheet(wb, t.code, db, version_id, college_name, teacher_id=t.id)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
