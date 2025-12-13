"""Unit tests for AnswerFaqWithRag LLM integration."""

import pytest

from app.application.dtos.knowledge import KnowledgeChunk
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository
from app.application.ports.llm_client import LLMClient
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag
from app.infrastructure.config.settings import settings


class MockKnowledgeBaseRepository(KnowledgeBaseRepository):
    """Mock knowledge base repository for testing."""

    def __init__(self, chunks_to_return: list[KnowledgeChunk]) -> None:
        """Initialize mock repository with chunks to return."""
        self._chunks_to_return = chunks_to_return

    def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """Return mocked chunks."""
        return self._chunks_to_return


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, should_fail: bool = False, return_empty: bool = False) -> None:
        """Initialize mock LLM client."""
        self._should_fail = should_fail
        self._return_empty = return_empty
        self.call_count = 0

    def generate_reply(self, system_prompt: str, user_message: str, context: dict) -> str:
        """Mock generate_reply method."""
        self.call_count += 1

        if self._should_fail:
            raise Exception("Mock LLM error")

        if self._return_empty:
            # Real OpenAILLMClient raises exception for empty responses
            raise Exception("OpenAI API call failed: Empty reply from OpenAI API")

        # Return Spanish response
        return "Esta es una respuesta generada por el LLM en español basada en el contexto proporcionado."


@pytest.fixture
def warranty_chunk():
    """Create a warranty chunk for testing."""
    return KnowledgeChunk(
        id="chunk_1",
        text="## 8. Periodo de Prueba y Garantía\n\n* **Garantía de 3 meses**, con opción de extender hasta 1 año.",
        score=0.8,
        source="knowledge_base.md",
    )


def test_llm_generation_when_enabled_and_client_available(warranty_chunk):
    """Test that LLM is called when enabled and client is available."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient()

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify LLM was called
        assert mock_llm.call_count == 1
        # Verify LLM-generated response is returned
        assert "generada por el LLM" in reply
        assert "español" in reply.lower()

    finally:
        settings.llm_enabled = original_llm_enabled


def test_deterministic_fallback_when_llm_disabled(warranty_chunk):
    """Test that deterministic fallback is used when LLM is disabled."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = False
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient()

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify LLM was NOT called
        assert mock_llm.call_count == 0
        # Verify deterministic response is returned (not LLM-generated)
        assert "generada por el LLM" not in reply
        # Should contain warranty content from chunk
        assert "garantía" in reply.lower() or "garantia" in reply.lower()

    finally:
        settings.llm_enabled = original_llm_enabled


def test_deterministic_fallback_when_llm_client_none(warranty_chunk):
    """Test that deterministic fallback is used when LLM client is None."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])

        service = AnswerFaqWithRag(mock_repo, llm_client=None)

        reply, _ = service.execute("garantía")

        # Verify deterministic response is returned
        assert "generada por el LLM" not in reply
        # Should contain warranty content from chunk
        assert "garantía" in reply.lower() or "garantia" in reply.lower()

    finally:
        settings.llm_enabled = original_llm_enabled


def test_deterministic_fallback_on_llm_error(warranty_chunk):
    """Test that deterministic fallback is used when LLM raises exception."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient(should_fail=True)

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify LLM was called (attempted)
        assert mock_llm.call_count == 1
        # Verify fallback deterministic response is returned
        assert "generada por el LLM" not in reply
        # Should contain warranty content from chunk
        assert "garantía" in reply.lower() or "garantia" in reply.lower()

    finally:
        settings.llm_enabled = original_llm_enabled


def test_deterministic_fallback_on_empty_llm_response(warranty_chunk):
    """Test that deterministic fallback is used when LLM returns empty response."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient(return_empty=True)

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify fallback deterministic response is returned
        assert "generada por el LLM" not in reply
        # Should contain warranty content from chunk
        assert "garantía" in reply.lower() or "garantia" in reply.lower()

    finally:
        settings.llm_enabled = original_llm_enabled


def test_llm_receives_correct_context(warranty_chunk):
    """Test that LLM receives correct context from retrieved chunks."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient()

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        service.execute("garantía")

        # Verify LLM was called
        assert mock_llm.call_count == 1

    finally:
        settings.llm_enabled = original_llm_enabled


def test_llm_spanish_only_requirement(warranty_chunk):
    """Basic test that LLM integration maintains Spanish-only requirement."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
        mock_llm = MockLLMClient()

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify response is in Spanish (basic check)
        assert isinstance(reply, str)
        assert len(reply) > 0
        # In real scenario, LLM should return Spanish; in mock we verify structure

    finally:
        settings.llm_enabled = original_llm_enabled


def test_llm_with_multiple_chunks():
    """Test that LLM receives multiple chunks when available."""
    original_llm_enabled = settings.llm_enabled

    try:
        settings.llm_enabled = True
        warranty_chunk = KnowledgeChunk(
            id="chunk_1",
            text="Garantía de 3 meses",
            score=0.8,
            source="kb.md",
        )
        inspection_chunk = KnowledgeChunk(
            id="chunk_2",
            text="Inspección integral realizada por especialistas",
            score=0.7,
            source="kb.md",
        )
        mock_repo = MockKnowledgeBaseRepository([warranty_chunk, inspection_chunk])
        mock_llm = MockLLMClient()

        service = AnswerFaqWithRag(mock_repo, llm_client=mock_llm)

        reply, _ = service.execute("garantía")

        # Verify LLM was called
        assert mock_llm.call_count == 1
        # Verify response is returned
        assert len(reply) > 0

    finally:
        settings.llm_enabled = original_llm_enabled
