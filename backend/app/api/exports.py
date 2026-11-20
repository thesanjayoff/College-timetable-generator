from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import require_read_access
from app.exporter.excel_exporter import export_all_sections_excel, export_all_teachers_excel, export_grid_excel
from app.exporter.ical_exporter import export_ical
from app.exporter.pdf_exporter import export_grid_pdf

router = APIRouter(prefix="/api/versions/{version_id}/export", tags=["export"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/excel/section/{section_id}", dependencies=[Depends(require_read_access)])
def excel_section(version_id: int, section_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_excel(db, version_id, f"Section {section_id}", college_name, section_id=section_id)
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": f"attachment; filename=section_{section_id}.xlsx"})


@router.get("/excel/teacher/{teacher_id}", dependencies=[Depends(require_read_access)])
def excel_teacher(version_id: int, teacher_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_excel(db, version_id, f"Teacher {teacher_id}", college_name, teacher_id=teacher_id)
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": f"attachment; filename=teacher_{teacher_id}.xlsx"})


@router.get("/excel/room/{room_id}", dependencies=[Depends(require_read_access)])
def excel_room(version_id: int, room_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_excel(db, version_id, f"Room {room_id}", college_name, room_id=room_id)
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": f"attachment; filename=room_{room_id}.xlsx"})


@router.get("/excel/all-sections", dependencies=[Depends(require_read_access)])
def excel_all_sections(version_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_all_sections_excel(db, version_id, college_name)
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": "attachment; filename=all_sections.xlsx"})


@router.get("/excel/all-teachers", dependencies=[Depends(require_read_access)])
def excel_all_teachers(version_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_all_teachers_excel(db, version_id, college_name)
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": "attachment; filename=all_teachers.xlsx"})


@router.get("/pdf/section/{section_id}", dependencies=[Depends(require_read_access)])
def pdf_section(version_id: int, section_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_pdf(db, version_id, f"Section {section_id}", college_name, section_id=section_id)
    return Response(content=data, media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename=section_{section_id}.pdf"})


@router.get("/pdf/teacher/{teacher_id}", dependencies=[Depends(require_read_access)])
def pdf_teacher(version_id: int, teacher_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_pdf(db, version_id, f"Teacher {teacher_id}", college_name, teacher_id=teacher_id)
    return Response(content=data, media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename=teacher_{teacher_id}.pdf"})


@router.get("/pdf/room/{room_id}", dependencies=[Depends(require_read_access)])
def pdf_room(version_id: int, room_id: int, college_name: str = "", db: Session = Depends(get_db)):
    data = export_grid_pdf(db, version_id, f"Room {room_id}", college_name, room_id=room_id)
    return Response(content=data, media_type="application/pdf",
                     headers={"Content-Disposition": f"attachment; filename=room_{room_id}.pdf"})


@router.get("/ical/teacher/{teacher_id}", dependencies=[Depends(require_read_access)])
def ical_teacher(version_id: int, teacher_id: int, term_start: date = Query(...), term_weeks: int = 16,
                  db: Session = Depends(get_db)):
    data = export_ical(db, version_id, term_start, term_weeks, teacher_id=teacher_id)
    return Response(content=data, media_type="text/calendar",
                     headers={"Content-Disposition": f"attachment; filename=teacher_{teacher_id}.ics"})


@router.get("/ical/section/{section_id}", dependencies=[Depends(require_read_access)])
def ical_section(version_id: int, section_id: int, term_start: date = Query(...), term_weeks: int = 16,
                  db: Session = Depends(get_db)):
    data = export_ical(db, version_id, term_start, term_weeks, section_id=section_id)
    return Response(content=data, media_type="text/calendar",
                     headers={"Content-Disposition": f"attachment; filename=section_{section_id}.ics"})
