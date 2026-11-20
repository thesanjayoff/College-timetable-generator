from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
import app.models  # noqa: registers all ORM models before create_all

from app.api import (
    allocations, auth, combined_classes, departments, electives, exports, imports,
    programs, public, rooms, sections, solve, subjects, substitution, teachers, time_structures,
    users, versions, weight_profiles,
)
from app.seed.create_admin import create_default_admin

app = FastAPI(title="College Timetable Generator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    auth, users, departments, programs, sections, time_structures, subjects, teachers,
    rooms, allocations, electives, combined_classes, weight_profiles, versions, solve,
    substitution, exports, imports, public,
):
    app.include_router(module.router)

if hasattr(sections, "lab_batches_router"):
    app.include_router(sections.lab_batches_router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
