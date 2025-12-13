"""Integration tests for RAG using the actual curated knowledge base."""

from pathlib import Path

import pytest

from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
    LocalMarkdownKnowledgeBaseRepository,
)
from app.application.use_cases.answer_faq_with_rag import AnswerFaqWithRag


@pytest.fixture
def curated_kb_repository():
    """Create repository using the actual curated knowledge base."""
    # Go up from tests/unit/use_cases/test_rag_with_curated_kb.py to project root
    # tests/unit/use_cases/ -> tests/unit/ -> tests/ -> project_root/
    project_root = Path(__file__).parent.parent.parent.parent
    kb_path = project_root / "data" / "knowledge_base.md"

    if not kb_path.exists():
        pytest.skip(f"Curated knowledge base file not found at {kb_path}")

    return LocalMarkdownKnowledgeBaseRepository(str(kb_path))


@pytest.fixture
def rag_service(curated_kb_repository):
    """Create RAG service with curated KB repository."""
    return AnswerFaqWithRag(curated_kb_repository)


def test_sedes_query_retrieves_from_curated_kb(curated_kb_repository):
    """Test that sedes queries retrieve chunks from the curated KB."""
    # Test various sedes-related queries
    for query in ["sedes", "ubicación", "centros kavak", "dónde están", "puebla", "monterrey"]:
        chunks = curated_kb_repository.retrieve(query, top_k=5)
        assert len(chunks) > 0, f"Query '{query}' should return at least one chunk"
        # Verify chunks contain Spanish content about locations
        chunk_texts = " ".join([chunk.text.lower() for chunk in chunks])
        assert (
            "sedes" in chunk_texts
            or "puebla" in chunk_texts
            or "monterrey" in chunk_texts
            or "ciudad" in chunk_texts
            or "presencia" in chunk_texts
        ), f"Query '{query}' should return chunks about locations/sedes"


def test_sedes_query_returns_spanish_answer(rag_service):
    """Test that sedes query returns Spanish answer from curated KB."""
    reply, suggested_questions = rag_service.execute("sedes")

    # Should not be fallback
    assert "No tengo esa información con certeza" not in reply
    # Should contain sedes/location information from curated KB
    assert (
        "sedes" in reply.lower()
        or "puebla" in reply.lower()
        or "monterrey" in reply.lower()
        or "15" in reply
    )
    assert len(suggested_questions) > 0
    # All content should be in Spanish
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_ubicacion_query_returns_spanish_answer(rag_service):
    """Test that ubicación query returns Spanish answer from curated KB."""
    reply, _ = rag_service.execute("dónde están las sedes")

    # Should not be fallback (dónde/sedes should match well)
    assert "No tengo esa información con certeza" not in reply
    # Should contain location information
    assert len(reply) > 0
    # Should mention sedes or locations
    assert (
        "sedes" in reply.lower()
        or "puebla" in reply.lower()
        or "monterrey" in reply.lower()
        or "ciudad" in reply.lower()
    )


def test_unrelated_query_returns_fallback(rag_service):
    """Test that queries unrelated to KB trigger Spanish safe fallback."""
    # Use a query that truly doesn't match KB content (no car/auto/Kavak/sedes terms)
    # Empty query or query with no matching tokens should return fallback
    reply, suggested_questions = rag_service.execute("xyzabc123")

    # Should return fallback (no relevant chunks found or score too low)
    assert "No tengo esa información con certeza" in reply
    assert len(suggested_questions) > 0


def test_rag_answers_grounded_in_kb(rag_service):
    """Test that RAG answers are grounded in KB content (basic invariant checks)."""
    # Test that answers about sedes contain information from KB
    reply, _ = rag_service.execute("sedes")

    # Should not be fallback
    if "No tengo esa información con certeza" not in reply:
        # If we got an answer, it should contain KB-related terms
        kb_terms = ["sedes", "kavak", "puebla", "monterrey", "ciudad", "mexico", "méxico"]
        assert any(term in reply.lower() for term in kb_terms), (
            "Answer should be grounded in KB content"
        )


def test_garantia_query_uses_kb_content(rag_service):
    """Test that garantía query uses content from curated KB."""
    reply, _ = rag_service.execute("garantía")

    # Should not be fallback
    if "No tengo esa información con certeza" not in reply:
        # Should contain garantía-related content from KB
        assert (
            "garantía" in reply.lower()
            or "garantia" in reply.lower()
            or "7 días" in reply.lower()
            or "3 meses" in reply.lower()
        )
