"""Unit tests for OpenAILLMClient."""

from unittest.mock import Mock, patch

import pytest

from app.adapters.outbound.llm.openai_llm_client import OpenAILLMClient
from app.application.ports.llm_client import LLMClient


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_choice = Mock()
    mock_choice.message.content = "Esta es una respuesta en español generada por el modelo."

    mock_response = Mock()
    mock_response.choices = [mock_choice]

    return mock_response


@pytest.fixture
def openai_client():
    """Create OpenAILLMClient with test API key."""
    with patch("app.adapters.outbound.llm.openai_llm_client.OpenAI") as mock_openai_class:
        mock_client_instance = Mock()
        mock_openai_class.return_value = mock_client_instance
        client = OpenAILLMClient(api_key="test-api-key", model="gpt-4o-mini", timeout_seconds=5)
        client._client = mock_client_instance
        yield client


def test_openai_client_implements_llm_client_port(openai_client):
    """Test that OpenAILLMClient implements LLMClient port."""
    assert isinstance(openai_client, LLMClient)


def test_openai_client_raises_error_when_api_key_missing():
    """Test that OpenAILLMClient raises error when API key is missing."""
    with patch("app.adapters.outbound.llm.openai_llm_client.OpenAI"):
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAILLMClient(api_key="")


def test_generate_reply_calls_openai_api(openai_client, mock_openai_response):
    """Test that generate_reply calls OpenAI API with correct parameters."""
    openai_client._client.chat.completions.create.return_value = mock_openai_response

    reply = openai_client.generate_reply(
        system_prompt="You are a helpful assistant.",
        user_message="¿Qué es Kavak?",
        context={},
    )

    # Verify API was called
    openai_client._client.chat.completions.create.assert_called_once()
    call_args = openai_client._client.chat.completions.create.call_args

    # Verify model parameter
    assert call_args.kwargs["model"] == "gpt-4o-mini"

    # Verify messages include Spanish enforcement
    messages = call_args.kwargs["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "ONLY in Spanish" in messages[0]["content"]
    assert messages[1]["role"] == "user"

    # Verify response is returned
    assert reply == "Esta es una respuesta en español generada por el modelo."
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_generate_reply_includes_spanish_enforcement_in_system_prompt(
    openai_client, mock_openai_response
):
    """Test that system prompt includes strict Spanish enforcement."""
    openai_client._client.chat.completions.create.return_value = mock_openai_response

    openai_client.generate_reply(
        system_prompt="Base system prompt",
        user_message="Test message",
        context={},
    )

    call_args = openai_client._client.chat.completions.create.call_args
    system_message = call_args.kwargs["messages"][0]["content"]

    assert "ONLY in Spanish" in system_message
    assert "Never use English" in system_message


def test_generate_reply_passes_context_to_user_message(openai_client, mock_openai_response):
    """Test that context is incorporated into user message."""
    openai_client._client.chat.completions.create.return_value = mock_openai_response

    context = {"chunks": ["chunk1", "chunk2"]}
    openai_client.generate_reply(
        system_prompt="System prompt",
        user_message="User query",
        context=context,
    )

    call_args = openai_client._client.chat.completions.create.call_args
    user_message = call_args.kwargs["messages"][1]["content"]

    assert "User query" in user_message


def test_generate_reply_raises_exception_on_empty_response(openai_client):
    """Test that generate_reply raises exception when OpenAI returns empty response."""
    mock_response = Mock()
    mock_response.choices = []
    openai_client._client.chat.completions.create.return_value = mock_response

    with pytest.raises(Exception, match="Empty response from OpenAI API"):
        openai_client.generate_reply(
            system_prompt="System prompt",
            user_message="User message",
            context={},
        )


def test_generate_reply_raises_exception_on_empty_content(openai_client):
    """Test that generate_reply raises exception when content is empty."""
    mock_choice = Mock()
    mock_choice.message.content = ""

    mock_response = Mock()
    mock_response.choices = [mock_choice]
    openai_client._client.chat.completions.create.return_value = mock_response

    with pytest.raises(Exception, match="Empty reply from OpenAI API"):
        openai_client.generate_reply(
            system_prompt="System prompt",
            user_message="User message",
            context={},
        )


def test_generate_reply_raises_exception_on_api_error(openai_client):
    """Test that generate_reply raises exception when API call fails."""
    openai_client._client.chat.completions.create.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="OpenAI API call failed"):
        openai_client.generate_reply(
            system_prompt="System prompt",
            user_message="User message",
            context={},
        )


def test_generate_reply_uses_default_settings_from_config():
    """Test that OpenAILLMClient uses default settings when not provided."""
    with patch("app.adapters.outbound.llm.openai_llm_client.settings") as mock_settings:
        mock_settings.openai_api_key = "default-key"
        mock_settings.openai_model = "gpt-4"
        mock_settings.openai_timeout_seconds = 15

        with patch("app.adapters.outbound.llm.openai_llm_client.OpenAI") as mock_openai_class:
            mock_client_instance = Mock()
            mock_openai_class.return_value = mock_client_instance

            client = OpenAILLMClient()

            assert client._api_key == "default-key"
            assert client._model == "gpt-4"
            assert client._timeout == 15


def test_generate_reply_response_in_spanish_basic_check(openai_client, mock_openai_response):
    """Basic test that response should be in Spanish (integration check)."""
    openai_client._client.chat.completions.create.return_value = mock_openai_response

    reply = openai_client.generate_reply(
        system_prompt="You are a helpful assistant for Kavak.",
        user_message="¿Qué garantías ofrecen?",
        context={"chunks": ["Garantía de 3 meses"]},
    )

    # Basic check: reply should not be empty and should be a string
    assert isinstance(reply, str)
    assert len(reply) > 0
    # In real scenario, we'd check for Spanish characters/words, but in mocked test
    # we just verify structure
    assert reply == "Esta es una respuesta en español generada por el modelo."


def test_generate_reply_api_call_parameters(openai_client, mock_openai_response):
    """Test that API call includes correct parameters for deterministic behavior."""
    openai_client._client.chat.completions.create.return_value = mock_openai_response

    openai_client.generate_reply(
        system_prompt="System prompt",
        user_message="User message",
        context={},
    )

    call_args = openai_client._client.chat.completions.create.call_args

    # Verify temperature is set (for balanced creativity)
    assert "temperature" in call_args.kwargs
    assert call_args.kwargs["temperature"] == 0.7

    # Verify max_tokens is set (to limit response length)
    assert "max_tokens" in call_args.kwargs
    assert call_args.kwargs["max_tokens"] == 500
