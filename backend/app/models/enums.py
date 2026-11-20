import enum


class SubjectType(str, enum.Enum):
    THEORY = "theory"
    LAB = "lab"
    TUTORIAL = "tutorial"
    PROJECT = "project"
    LIBRARY = "library"
    SPORTS = "sports"
    MENTORING = "mentoring"
    OPEN_ELECTIVE = "open_elective"
    PROFESSIONAL_ELECTIVE = "professional_elective"


class RoomType(str, enum.Enum):
    CLASSROOM = "classroom"
    LAB = "lab"
    SEMINAR_HALL = "seminar_hall"


class PeriodKind(str, enum.Enum):
    TEACHING = "teaching"
    BREAK = "break"
    LUNCH = "lunch"


class SessionKind(str, enum.Enum):
    REGULAR = "regular"
    COMBINED = "combined"
    ELECTIVE = "elective"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    VIEWER = "viewer"


class VersionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PreferenceType(str, enum.Enum):
    PREFERRED_DAY = "preferred_day"
    FREE_DAY = "free_day"
    NO_FIRST_PERIOD = "no_first_period"
    NO_LAST_PERIOD = "no_last_period"
    AVOID_BACK_TO_BACK = "avoid_back_to_back"
    SAME_ROOM = "same_room"


class SolveStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    FEASIBLE = "feasible"
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    STOPPED = "stopped"
    FAILED = "failed"
