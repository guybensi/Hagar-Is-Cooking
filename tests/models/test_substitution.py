import pytest
from pydantic import ValidationError

from app.models.substitution import (
    SubstitutionAction,
    SubstitutionAnswer,
    SubstitutionDecision,
    SubstitutionDecisionList,
)


def test_substitute_action_requires_replacement():
    with pytest.raises(ValidationError):
        SubstitutionDecision(
            ingredient_name="Celery root",
            action=SubstitutionAction.SUBSTITUTE,
            reason="Similar flavor",
        )


def test_substitute_action_with_replacement_is_valid():
    decision = SubstitutionDecision(
        ingredient_name="Celery root",
        action=SubstitutionAction.SUBSTITUTE,
        reason="Similar flavor",
        replacement="Parsley root",
    )
    assert decision.replacement == "Parsley root"


def test_skip_action_does_not_require_replacement():
    decision = SubstitutionDecision(
        ingredient_name="Basil", action=SubstitutionAction.SKIP, reason="Optional"
    )
    assert decision.replacement is None


def test_buy_action_does_not_require_replacement():
    decision = SubstitutionDecision(
        ingredient_name="Ground beef", action=SubstitutionAction.BUY, reason="Main ingredient"
    )
    assert decision.replacement is None


def test_substitution_decision_list_wraps_decisions():
    decision_list = SubstitutionDecisionList(
        decisions=[
            SubstitutionDecision(
                ingredient_name="Basil", action=SubstitutionAction.SKIP, reason="Optional"
            )
        ]
    )
    assert len(decision_list.decisions) == 1


def test_substitution_answer_defaults_to_unanswered():
    answer = SubstitutionAnswer(ingredient_name="Celery root")
    assert answer.accepted is None
