import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.orm import Session

from app.exporter.common import cell_label, get_default_structure, sessions_for_view, structure_grid_labels


def export_grid_pdf(db: Session, version_id: int, title: str, college_name: str = "",
                     section_id=None, teacher_id=None, room_id=None) -> bytes:
    structure = get_default_structure(db)
    days, periods = structure_grid_labels(structure)
    sessions = sessions_for_view(db, version_id, section_id, teacher_id, room_id)
    by_slot = {}
    for s in sessions:
        by_slot.setdefault((s.day_index, s.period_index), []).append(s)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                             topMargin=10 * mm, bottomMargin=10 * mm)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"{college_name} &mdash; {title}", styles["Title"]), Spacer(1, 8)]

    header = ["Period"] + [d.name for d in days]
    data = [header]
    for p in periods:
        if p.kind.value != "teaching":
            row = ["Lunch" if p.kind.value == "lunch" else "Break"] + ["" for _ in days]
        else:
            row = [f"{p.label}\n{p.start_time}-{p.end_time}"]
            for d in days:
                if d.max_period_index is not None and p.period_index > d.max_period_index:
                    row.append("-")
                    continue
                matches = by_slot.get((d.day_index, p.period_index), [])
                row.append("\n".join(cell_label(m) for m in matches))
        data.append(row)

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
    ]))
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()
