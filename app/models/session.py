from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.recipe import ExtractedRecipe, FinalRecipe, StructuredRecipe
from app.models.search import SearchResult
from app.models.substitution import SubstitutionAnswer, SubstitutionDecision


class SessionState(StrEnum):
    IDLE = "IDLE"
    AWAITING_DISH_QUERY = "AWAITING_DISH_QUERY"
    SEARCHING = "SEARCHING"
    AWAITING_RECIPE_SELECTION = "AWAITING_RECIPE_SELECTION"
    EXTRACTING = "EXTRACTING"
    STRUCTURING = "STRUCTURING"
    AWAITING_CHECKLIST = "AWAITING_CHECKLIST"
    DECIDING_SUBSTITUTIONS = "DECIDING_SUBSTITUTIONS"
    AWAITING_SUBSTITUTION_ANSWERS = "AWAITING_SUBSTITUTION_ANSWERS"
    GENERATING_FINAL_RECIPE = "GENERATING_FINAL_RECIPE"
    AWAITING_DELIVERY_MODE = "AWAITING_DELIVERY_MODE"
    DELIVERING_FULL = "DELIVERING_FULL"
    DELIVERING_INTERACTIVE = "DELIVERING_INTERACTIVE"
    COMPLETED = "COMPLETED"


# States in which the free-text message handler is allowed to start a new search.
QUERY_ACCEPTING_STATES = {
    SessionState.IDLE,
    SessionState.AWAITING_DISH_QUERY,
    SessionState.COMPLETED,
}

# States that mark "mid external call" (Groq/Tavily/httpx in flight). A crash or restart while
# in one of these can never be resumed -- there is no in-progress request to reconnect to -- so
# the safest recovery is to reset back to IDLE rather than leave the user stranded.
TRANSIENT_STATES = {
    SessionState.SEARCHING,
    SessionState.EXTRACTING,
    SessionState.STRUCTURING,
    SessionState.DECIDING_SUBSTITUTIONS,
    SessionState.GENERATING_FINAL_RECIPE,
}


class ChecklistItem(BaseModel):
    name: str
    amount: str | None = None
    checked: bool = True


class SessionData(BaseModel):
    chat_id: int
    state: SessionState = SessionState.IDLE

    dish_query: str | None = None
    search_results: list[SearchResult] = Field(default_factory=list)
    selected_index: int | None = None

    extracted_recipe: ExtractedRecipe | None = None
    structured_recipe: StructuredRecipe | None = None

    checklist: list[ChecklistItem] = Field(default_factory=list)
    substitution_decisions: list[SubstitutionDecision] = Field(default_factory=list)
    substitution_answers: list[SubstitutionAnswer] = Field(default_factory=list)
    pending_substitution_index: int = 0

    final_recipe: FinalRecipe | None = None
    delivery_mode: Literal["full", "interactive"] | None = None
    current_step_index: int = 0

    last_bot_message_id: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
