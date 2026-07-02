from enum import StrEnum

from pydantic import BaseModel, model_validator


class SubstitutionAction(StrEnum):
    BUY = "BUY"
    SKIP = "SKIP"
    SUBSTITUTE = "SUBSTITUTE"


class SubstitutionDecision(BaseModel):
    ingredient_name: str
    action: SubstitutionAction
    reason: str
    replacement: str | None = None

    @model_validator(mode="after")
    def _replacement_required_for_substitute(self) -> "SubstitutionDecision":
        if self.action == SubstitutionAction.SUBSTITUTE and not self.replacement:
            raise ValueError("replacement is required when action is SUBSTITUTE")
        return self


class SubstitutionDecisionList(BaseModel):
    """Top-level wrapper: Groq's json_schema mode requires a JSON object, not a bare array."""

    decisions: list[SubstitutionDecision]


class SubstitutionAnswer(BaseModel):
    ingredient_name: str
    accepted: bool | None = None
