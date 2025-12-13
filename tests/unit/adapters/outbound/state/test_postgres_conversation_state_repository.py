"""Unit tests for Postgres conversation state repository using SQLite in-memory."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.state.models import Base
from app.adapters.outbound.state.postgres_conversation_state_repository import (
    PostgresConversationStateRepository,
)
from app.domain.entities.conversation_state import ConversationState


@pytest.fixture
def sqlite_engine():
    """Create SQLite in-memory engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(sqlite_engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(sqlite_engine, monkeypatch):
    """Create Postgres repository with SQLite in-memory database for testing."""
    # Patch get_db_session to use our test session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

    def get_test_db_session():
        return SessionLocal()

    monkeypatch.setattr(
        "app.adapters.outbound.state.postgres_conversation_state_repository.get_db_session",
        get_test_db_session,
    )

    return PostgresConversationStateRepository()


@pytest.mark.asyncio
async def test_save_and_get_round_trip(repository):
    """Test that saving and getting a state works correctly."""
    session_id = "test_session_1"
    state = ConversationState(
        session_id=session_id,
        need="buy",
        budget="500000",
        step="budget",
    )

    # Save state
    await repository.save(session_id, state)

    # Get state
    retrieved = await repository.get(session_id)

    assert retrieved is not None
    assert retrieved.session_id == session_id
    assert retrieved.need == "buy"
    assert retrieved.budget == "500000"
    assert retrieved.step == "budget"


@pytest.mark.asyncio
async def test_get_nonexistent_session(repository):
    """Test that getting a non-existent session returns None."""
    result = await repository.get("nonexistent_session")
    assert result is None


@pytest.mark.asyncio
async def test_save_updates_existing_row(repository):
    """Test that saving to an existing session updates the row."""
    session_id = "test_session_2"
    initial_state = ConversationState(
        session_id=session_id,
        need="buy",
        budget="300000",
        step="budget",
    )

    # Save initial state
    await repository.save(session_id, initial_state)

    # Update state
    updated_state = ConversationState(
        session_id=session_id,
        need="buy",
        budget="500000",  # Changed
        preferences="Toyota",  # Added
        step="options",  # Changed
    )
    await repository.save(session_id, updated_state)

    # Retrieve and verify
    retrieved = await repository.get(session_id)
    assert retrieved is not None
    assert retrieved.budget == "500000"
    assert retrieved.preferences == "Toyota"
    assert retrieved.step == "options"


@pytest.mark.asyncio
async def test_delete_session(repository):
    """Test that deleting a session removes it."""
    session_id = "test_session_3"
    state = ConversationState(session_id=session_id, need="buy")

    # Save state
    await repository.save(session_id, state)

    # Verify it exists
    assert await repository.get(session_id) is not None

    # Delete it
    await repository.delete(session_id)

    # Verify it's gone
    assert await repository.get(session_id) is None


@pytest.mark.asyncio
async def test_save_preserves_timestamps(repository):
    """Test that timestamps are preserved correctly."""
    session_id = "test_session_4"
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    updated_at = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

    state = ConversationState(
        session_id=session_id,
        need="buy",
        created_at=created_at,
        updated_at=updated_at,
    )

    # Save state
    await repository.save(session_id, state)

    # Retrieve and verify timestamps
    retrieved = await repository.get(session_id)
    assert retrieved is not None
    assert retrieved.created_at == created_at
    assert retrieved.updated_at == updated_at


@pytest.mark.asyncio
async def test_save_all_fields(repository):
    """Test that all ConversationState fields are saved and retrieved correctly."""
    session_id = "test_session_5"
    state = ConversationState(
        session_id=session_id,
        need="buy",
        budget="500000",
        preferences="Toyota Corolla",
        financing_interest=True,
        down_payment="100000",
        loan_term=60,
        selected_car_price=450000.0,
        last_question="What's your budget?",
        step="financing",
        lead_name="John Doe",
        lead_phone="+521234567890",
        lead_preferred_contact_time="morning",
    )

    await repository.save(session_id, state)
    retrieved = await repository.get(session_id)

    assert retrieved is not None
    assert retrieved.need == "buy"
    assert retrieved.budget == "500000"
    assert retrieved.preferences == "Toyota Corolla"
    assert retrieved.financing_interest is True
    assert retrieved.down_payment == "100000"
    assert retrieved.loan_term == 60
    assert retrieved.selected_car_price == 450000.0
    assert retrieved.last_question == "What's your budget?"
    assert retrieved.step == "financing"
    assert retrieved.lead_name == "John Doe"
    assert retrieved.lead_phone == "+521234567890"
    assert retrieved.lead_preferred_contact_time == "morning"


@pytest.mark.asyncio
async def test_multiple_sessions(repository):
    """Test that multiple sessions can coexist."""
    session1 = "session_1"
    session2 = "session_2"

    state1 = ConversationState(session_id=session1, need="buy", budget="300000")
    state2 = ConversationState(session_id=session2, need="sell", budget="200000")

    await repository.save(session1, state1)
    await repository.save(session2, state2)

    retrieved1 = await repository.get(session1)
    retrieved2 = await repository.get(session2)

    assert retrieved1 is not None
    assert retrieved1.session_id == session1
    assert retrieved1.need == "buy"

    assert retrieved2 is not None
    assert retrieved2.session_id == session2
    assert retrieved2.need == "sell"
