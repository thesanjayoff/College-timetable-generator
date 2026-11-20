from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.importer.excel_importer import import_workbook
from app.importer.templates import generate_template_workbook

router = APIRouter(prefix="/api/import", tags=["import"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template")
def download_template():
    data = generate_template_workbook()
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": "attachment; filename=timetable_import_template.xlsx"})


@router.post("/excel")
async def import_excel(file: UploadFile = File(...), dry_run: bool = Query(False), db: Session = Depends(get_db)):
    content = await file.read()
    report = import_workbook(db, content, dry_run=dry_run)
    return report.to_dict()
