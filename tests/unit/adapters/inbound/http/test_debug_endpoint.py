"""Unit tests for debug endpoint."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.adapters.inbound.http.routes import router
from app.infrastructure.config.settings import settings


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.asyncio
async def test_debug_endpoint_disabled_returns_404(client):
    """Test that debug endpoint returns 404 when DEBUG_MODE is disabled."""
    with patch.object(settings, "debug_mode", False):
        response = client.get("/debug/session/test_session")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_debug_endpoint_enabled_returns_state(client):
    """Test that debug endpoint returns state when DEBUG_MODE is enabled."""
    with patch.object(settings, "debug_mode", True):
        # First create a session by making a chat request
        chat_response = client.post(
            "/chat",
            json={
                "session_id": "test_debug_session",
                "message": "Estoy buscando un auto familiar",
                "channel": "api",
            },
        )
        assert chat_response.status_code == status.HTTP_200_OK

        # Now check debug endpoint
        debug_response = client.get("/debug/session/test_debug_session")
        assert debug_response.status_code == status.HTTP_200_OK
        data = debug_response.json()
        assert "session_id" in data
        assert "state" in data
        assert data["session_id"] == "test_debug_session"
        # State should have English keys
        if data["state"] is not None:
            assert "step" in data["state"]
            assert "need" in data["state"]


@pytest.mark.asyncio
async def test_debug_endpoint_nonexistent_session(client):
    """Test that debug endpoint returns None state for nonexistent session."""
    with patch.object(settings, "debug_mode", True):
        response = client.get("/debug/session/nonexistent_session")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == "nonexistent_session"
        assert data["state"] is None
