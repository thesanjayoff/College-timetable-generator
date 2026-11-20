"""Shared FastAPI dependencies, re-exported for convenient importing by routers."""
from app.database import get_db
from app.core.security import (
    get_current_user,
    require_role,
    require_department_access,
    require_admin,
    require_write_access,
    require_read_access,
)

__all__ = [
    "get_db",
    "get_current_user",
    "require_role",
    "require_department_access",
    "require_admin",
    "require_write_access",
    "require_read_access",
]
