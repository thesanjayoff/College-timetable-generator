import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa
from app.importer.excel_importer import import_workbook
from app.importer.templates import generate_template_workbook
from app.models.allocation import Allocation
from app.models.college import Department


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_template_example_rows_import_cleanly():
    db = make_db()
    data = generate_template_workbook()
    report = import_workbook(db, data)
    assert report.errors == [], report.to_dict()
    assert report.committed, report.to_dict()
    assert db.query(Department).count() >= 2
    assert db.query(Allocation).count() >= 2


def test_bad_rows_are_reported_precisely():
    db = make_db()
    from openpyxl import Workbook
    import io
    wb = Workbook()
    ws = wb.active
    ws.title = "Departments"
    ws.append(["code", "name"])
    ws.append(["CSE", "Computer Science"])
    ws.append([None, "Missing code dept"])  # bad row: no code
    buf = io.BytesIO()
    wb.save(buf)

    report = import_workbook(db, buf.getvalue())
    assert not report.committed
    assert len(report.errors) == 1
    e = report.errors[0]
    assert e.sheet == "Departments"
    assert e.row == 3
    assert e.column == "code"


if __name__ == "__main__":
    test_template_example_rows_import_cleanly()
    test_bad_rows_are_reported_precisely()
    print("OK")
