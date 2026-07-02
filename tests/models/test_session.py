from app.models.session import (
    MODE_SWITCHABLE_STATES,
    QUERY_ACCEPTING_STATES,
    SessionData,
    SessionState,
)


def test_session_data_defaults():
    session = SessionData(chat_id=123)

    assert session.state == SessionState.IDLE
    assert session.search_results == []
    assert session.checklist == []
    assert session.pending_substitution_index == 0
    assert session.current_step_index == 0
    assert session.delivery_mode is None
    assert session.history_logged is False


def test_session_data_round_trips_through_json():
    session = SessionData(chat_id=123, state=SessionState.AWAITING_CHECKLIST, dish_query="פסטה")

    restored = SessionData.model_validate_json(session.model_dump_json())

    assert restored == session


def test_query_accepting_states_includes_idle_and_completed():
    assert SessionState.IDLE in QUERY_ACCEPTING_STATES
    assert SessionState.AWAITING_DISH_QUERY in QUERY_ACCEPTING_STATES
    assert SessionState.COMPLETED in QUERY_ACCEPTING_STATES
    assert SessionState.AWAITING_RECIPE_SELECTION not in QUERY_ACCEPTING_STATES


def test_mode_switchable_states_allow_toggling_after_delivery():
    assert SessionState.AWAITING_DELIVERY_MODE in MODE_SWITCHABLE_STATES
    assert SessionState.DELIVERING_INTERACTIVE in MODE_SWITCHABLE_STATES
    assert SessionState.COMPLETED in MODE_SWITCHABLE_STATES
    assert SessionState.AWAITING_CHECKLIST not in MODE_SWITCHABLE_STATES
