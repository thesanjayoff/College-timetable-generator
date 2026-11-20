from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)

    programs: Mapped[list["Program"]] = relationship(back_populates="department")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(20))
    duration_semesters: Mapped[int] = mapped_column(Integer, default=8)
    time_structure_id: Mapped[int | None] = mapped_column(ForeignKey("time_structures.id"), nullable=True)

    department: Mapped[Department] = relationship(back_populates="programs")
    sections: Mapped[list["Section"]] = relationship(back_populates="program")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"))
    semester_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(40))  # e.g. "A" -> displayed as CSE-A
    strength: Mapped[int] = mapped_column(Integer, default=60)
    time_structure_id: Mapped[int | None] = mapped_column(ForeignKey("time_structures.id"), nullable=True)
    max_periods_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_consecutive_periods: Mapped[int | None] = mapped_column(Integer, nullable=True)

    program: Mapped[Program] = relationship(back_populates="sections")
    lab_batches: Mapped[list["LabBatch"]] = relationship(back_populates="section", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        return f"{self.program.code}-{self.semester_number}-{self.name}"


class LabBatch(Base):
    __tablename__ = "lab_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    name: Mapped[str] = mapped_column(String(40))  # e.g. "A1"
    strength: Mapped[int] = mapped_column(Integer, default=30)

    section: Mapped[Section] = relationship(back_populates="lab_batches")
