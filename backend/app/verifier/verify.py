from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.weight import DEFAULT_WEIGHTS
from app.verifier.checks import Violation, check_all
from app.verifier.extract import build_verifier_input
from app.verifier.scorecard import compute_scorecard


@dataclass
class VerificationReport:
    version_id: int
    hard_violations: list[Violation] = field(default_factory=list)
    scorecard: dict = field(default_factory=dict)

    @property
    def is_clean(self) -> bool:
        return len(self.hard_violations) == 0

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "hard_violation_count": len(self.hard_violations),
            "is_clean": self.is_clean,
            "hard_violations": [
                {"category": v.category, "message": v.message, "details": v.details}
                for v in self.hard_violations
            ],
            "scorecard": self.scorecard,
        }


def verify_version(db: Session, version_id: int, weights: dict | None = None) -> VerificationReport:
    data = build_verifier_input(db, version_id)
    violations = check_all(data)
    scorecard = compute_scorecard(data, weights or DEFAULT_WEIGHTS)
    return VerificationReport(version_id=version_id, hard_violations=violations, scorecard=scorecard)
