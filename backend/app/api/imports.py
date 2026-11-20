from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, require_read_access, require_write_access
from app.importer.excel_importer import import_workbook
from app.importer.templates import generate_template_workbook
from app.models.user import User
from app.services.audit import log_action

router = APIRouter(prefix="/api/import", tags=["import"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template", dependencies=[Depends(require_read_access)])
def download_template():
    data = generate_template_workbook()
    return Response(content=data, media_type=XLSX_MEDIA,
                     headers={"Content-Disposition": "attachment; filename=timetable_import_template.xlsx"})


@router.post("/excel", dependencies=[Depends(require_write_access)])
async def import_excel(file: UploadFile = File(...), dry_run: bool = Query(False), db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    content = await file.read()
    report = import_workbook(db, content, dry_run=dry_run)
    if not dry_run:
        log_action(db, current_user, "import_excel", "excel_import", None,
                   {"filename": file.filename, "errors": len(report.errors)})
        db.commit()
    return report.to_dict()
