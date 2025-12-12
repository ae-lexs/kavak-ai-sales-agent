"""Unit tests for ConversationState entity."""

from app.domain.entities.conversation_state import ConversationState


def test_conversation_state_initialization():
    """Test ConversationState initialization."""
    state = ConversationState(session_id="test_session")

    assert state.session_id == "test_session"
    assert state.need is None
    assert state.budget is None
    assert state.preferences is None
    assert state.financing_interest is None
    assert state.contact_intent is None
    assert state.current_step == "need"


def test_conversation_state_is_complete():
    """Test ConversationState is_complete method."""
    state = ConversationState(session_id="test_session")
    assert state.is_complete() is False

    state.need = "family"
    state.budget = "$200,000"
    state.preferences = "automatic"
    state.financing_interest = True
    state.contact_intent = True

    assert state.is_complete() is True


def test_conversation_state_get_next_missing_field():
    """Test ConversationState get_next_missing_field method."""
    state = ConversationState(session_id="test_session")

    assert state.get_next_missing_field() == "need"

    state.need = "family"
    assert state.get_next_missing_field() == "budget"

    state.budget = "$200,000"
    assert state.get_next_missing_field() == "preferences"

    state.preferences = "automatic"
    assert state.get_next_missing_field() == "financing_interest"

    state.financing_interest = True
    assert state.get_next_missing_field() == "contact_intent"

    state.contact_intent = True
    assert state.get_next_missing_field() is None

