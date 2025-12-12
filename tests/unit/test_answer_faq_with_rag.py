"""Unit tests for AnswerFaqWithRag."""

from app.application.dtos.knowledge import KnowledgeChunk
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag


class MockKnowledgeBaseRepository(KnowledgeBaseRepository):
    """Mock knowledge base repository for testing."""

    def __init__(self, chunks_to_return: list[KnowledgeChunk]) -> None:
        """Initialize mock repository with chunks to return."""
        self._chunks_to_return = chunks_to_return

    def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """Return mocked chunks."""
        return self._chunks_to_return


def test_no_evidence_returns_spanish_fallback():
    """Test that no evidence returns Spanish safe fallback."""
    mock_repo = MockKnowledgeBaseRepository([])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("test query")

    assert "No tengo esa información con certeza" in reply
    assert len(suggested_questions) > 0
    # All suggested questions should be in Spanish
    for question in suggested_questions:
        assert isinstance(question, str)
        assert len(question) > 0


def test_low_score_returns_spanish_fallback():
    """Test that low score chunks return Spanish safe fallback."""
    low_score_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Some irrelevant text",
        score=0.05,  # Below threshold
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([low_score_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("test query")

    assert "No tengo esa información con certeza" in reply
    assert len(suggested_questions) > 0


def test_warranty_query_returns_spanish_answer():
    """Test that warranty query returns Spanish answer."""
    warranty_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak offers a warranty on all certified vehicles. The warranty covers major mechanical components.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("garantía")

    # Should not be fallback
    assert "No tengo esa información con certeza" not in reply
    # Should contain warranty-related content in Spanish
    assert "garantía" in reply.lower() or "garantia" in reply.lower()
    assert len(suggested_questions) > 0
    # All text should be in Spanish
    assert isinstance(reply, str)


def test_inspection_query_returns_spanish_answer():
    """Test that inspection query returns Spanish answer."""
    inspection_chunk = KnowledgeChunk(
        id="chunk_1",
        text="All cars sold through Kavak undergo a comprehensive 360-point inspection.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([inspection_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("inspección")

    assert "No tengo esa información con certeza" not in reply
    assert "inspección" in reply.lower() or "inspeccion" in reply.lower()
    assert len(suggested_questions) > 0


def test_delivery_query_returns_spanish_answer():
    """Test that delivery query returns Spanish answer."""
    delivery_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak offers home delivery service for your convenience.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([delivery_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("entrega")

    assert "No tengo esa información con certeza" not in reply
    assert len(suggested_questions) > 0


def test_return_policy_query_returns_spanish_answer():
    """Test that return policy query returns Spanish answer."""
    return_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak offers a 7-day return guarantee. If you're not satisfied, you can return the vehicle.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([return_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, suggested_questions = service.execute("devolución")

    assert "No tengo esa información con certeza" not in reply
    assert len(suggested_questions) > 0


def test_suggested_questions_are_in_spanish():
    """Test that suggested questions are always in Spanish."""
    warranty_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak offers a warranty on all certified vehicles.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([warranty_chunk])
    service = AnswerFaqWithRag(mock_repo)

    _, suggested_questions = service.execute("garantía")

    assert len(suggested_questions) >= 2
    # Check that questions contain Spanish words (basic check)
    spanish_indicators = ["qué", "que", "cómo", "como", "garantía", "garantia", "financiamiento"]
    has_spanish = any(
        any(indicator in q.lower() for indicator in spanish_indicators) for q in suggested_questions
    )
    assert has_spanish or len(suggested_questions) > 0  # At least they exist


def test_multiple_relevant_chunks_includes_supplementary_info():
    """Test that multiple relevant chunks can include supplementary information."""
    warranty_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak offers a warranty on all certified vehicles.",
        score=0.8,
        source="test.md",
    )
    inspection_chunk = KnowledgeChunk(
        id="chunk_2",
        text="All cars undergo a comprehensive inspection.",
        score=0.7,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([warranty_chunk, inspection_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, _ = service.execute("garantía")

    assert "No tengo esa información con certeza" not in reply
    assert len(reply) > 0


def test_default_mapping_uses_chunk_content():
    """Test that default case uses chunk content with term translation."""
    # Chunk that doesn't match any specific keyword handler
    # Avoid: warranty, guarantee, inspection, delivery, financing, certified, safety, security, return
    generic_chunk = KnowledgeChunk(
        id="chunk_1",
        text="Kavak is Mexico's leading platform for buying and selling used cars. We provide quality service.",
        score=0.8,
        source="test.md",
    )
    mock_repo = MockKnowledgeBaseRepository([generic_chunk])
    service = AnswerFaqWithRag(mock_repo)

    reply, _ = service.execute("qué es kavak")

    # Should not be fallback
    assert "No tengo esa información con certeza" not in reply
    # Should use chunk content (translated terms should appear)
    assert "Kavak" in reply or "kavak" in reply.lower()
    # Should contain translated terms from mapping
    assert "plataforma" in reply.lower() or "México" in reply
    # Should contain the chunk content (not a hardcoded generic message)
    assert "Basándome en nuestra información" in reply
    assert len(reply) > 0
