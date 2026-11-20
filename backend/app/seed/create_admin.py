"""Bootstraps a default admin user on first run."""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User

DEFAULT_ADMIN_EMAIL = "admin@timetable.app"
DEFAULT_ADMIN_PASSWORD = "admin123"


def create_default_admin(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    db.add(User(
        email=DEFAULT_ADMIN_EMAIL, hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
        name="Administrator", role=UserRole.ADMIN, is_active=True,
    ))
    db.commit()


if __name__ == "__main__":
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        create_default_admin(db)
        print(f"Default admin ensured: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")
    finally:
        db.close()
