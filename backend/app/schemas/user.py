from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole

# Deliberately permissive compared to pydantic's EmailStr/email-validator: this app is used on
# campus intranets where addresses like "admin@college.local" are common, and email-validator's
# default deliverability rules reject ".local" (and other special-use) domains outright. This
# pattern still rejects obviously malformed input (no "@", no domain, embedded whitespace, etc.)
# so bad input still 422s with a clear message, just without the reserved-TLD rejection.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserBase(BaseModel):
    email: str = Field(min_length=3, max_length=150, pattern=EMAIL_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.VIEWER
    department_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=150, pattern=EMAIL_PATTERN)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[UserRole] = None
    department_id: Optional[int] = Field(default=None, gt=0)
    teacher_id: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UserSelfUpdate(BaseModel):
    """What a non-admin user may change about themselves."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
