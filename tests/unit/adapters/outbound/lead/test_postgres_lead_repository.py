"""Unit tests for Postgres lead repository using SQLite in-memory."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.outbound.conversation_state_repository.models import Base
from app.adapters.outbound.lead.postgres_lead_repository import PostgresLeadRepository
from app.application.dtos.lead import Lead


@pytest.fixture
def sqlite_engine():
    """Create SQLite in-memory engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def repository(sqlite_engine, monkeypatch):
    """Create Postgres repository with SQLite in-memory database for testing."""
    # Patch get_db_session to use our test session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

    def get_test_db_session():
        return SessionLocal()

    monkeypatch.setattr(
        "app.adapters.outbound.lead.postgres_lead_repository.get_db_session",
        get_test_db_session,
    )

    return PostgresLeadRepository()


@pytest.mark.asyncio
async def test_save_and_list_round_trip(repository):
    """Test that saving and listing leads works correctly."""
    lead = Lead(
        session_id="test_session_1",
        name="John Doe",
        phone="+521234567890",
        preferred_contact_time="morning",
        created_at=datetime.now(timezone.utc),
    )

    # Save lead
    await repository.save(lead)

    # List leads
    leads = await repository.list()

    assert len(leads) == 1
    assert leads[0].session_id == "test_session_1"
    assert leads[0].name == "John Doe"
    assert leads[0].phone == "+521234567890"
    assert leads[0].preferred_contact_time == "morning"


@pytest.mark.asyncio
async def test_save_upsert_behavior(repository):
    """Test that saving to an existing session_id updates the lead."""
    session_id = "test_session_2"

    # Save partial lead
    partial_lead = Lead(
        session_id=session_id,
        name="Jane Doe",
        phone=None,
        preferred_contact_time=None,
        created_at=datetime.now(timezone.utc),
    )
    await repository.save(partial_lead)

    # Verify partial lead
    leads = await repository.list()
    assert len(leads) == 1
    assert leads[0].name == "Jane Doe"
    assert leads[0].phone is None

    # Save complete lead (upsert)
    complete_lead = Lead(
        session_id=session_id,
        name="Jane Doe",
        phone="+529876543210",
        preferred_contact_time="afternoon",
        created_at=datetime.now(timezone.utc),
    )
    await repository.save(complete_lead)

    # Verify updated lead
    leads = await repository.list()
    assert len(leads) == 1
    assert leads[0].session_id == session_id
    assert leads[0].name == "Jane Doe"
    assert leads[0].phone == "+529876543210"
    assert leads[0].preferred_contact_time == "afternoon"


@pytest.mark.asyncio
async def test_list_empty_repository(repository):
    """Test that listing from empty repository returns empty list."""
    leads = await repository.list()
    assert leads == []


@pytest.mark.asyncio
async def test_save_multiple_leads(repository):
    """Test that multiple leads can be saved and listed."""
    lead1 = Lead(
        session_id="session_1",
        name="Alice",
        phone="+1111111111",
        preferred_contact_time="morning",
        created_at=datetime.now(timezone.utc),
    )
    lead2 = Lead(
        session_id="session_2",
        name="Bob",
        phone="+2222222222",
        preferred_contact_time="evening",
        created_at=datetime.now(timezone.utc),
    )

    await repository.save(lead1)
    await repository.save(lead2)

    leads = await repository.list()
    assert len(leads) == 2

    # Verify both leads are present
    session_ids = {lead.session_id for lead in leads}
    assert "session_1" in session_ids
    assert "session_2" in session_ids

    # Verify details
    lead_dict = {lead.session_id: lead for lead in leads}
    assert lead_dict["session_1"].name == "Alice"
    assert lead_dict["session_2"].name == "Bob"


@pytest.mark.asyncio
async def test_save_preserves_created_at(repository):
    """Test that created_at timestamp is preserved on first save."""
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    lead = Lead(
        session_id="test_session_3",
        name="Test User",
        phone="+1234567890",
        preferred_contact_time="morning",
        created_at=created_at,
    )

    await repository.save(lead)

    leads = await repository.list()
    assert len(leads) == 1
    assert leads[0].created_at == created_at


@pytest.mark.asyncio
async def test_save_partial_lead(repository):
    """Test that partial leads (missing fields) can be saved."""
    partial_lead = Lead(
        session_id="test_session_4",
        name="Partial User",
        phone=None,
        preferred_contact_time=None,
        created_at=datetime.now(timezone.utc),
    )

    await repository.save(partial_lead)

    leads = await repository.list()
    assert len(leads) == 1
    assert leads[0].name == "Partial User"
    assert leads[0].phone is None
    assert leads[0].preferred_contact_time is None
