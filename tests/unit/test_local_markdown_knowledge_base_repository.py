"""Unit tests for LocalMarkdownKnowledgeBaseRepository."""

import tempfile
from pathlib import Path

import pytest

from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
    LocalMarkdownKnowledgeBaseRepository,
)


@pytest.fixture
def sample_knowledge_base():
    """Create a temporary knowledge base file for testing."""
    content = """# Kavak Value Proposition

## Guarantee and Certification

### 360-Point Inspection

All cars sold through Kavak undergo a comprehensive 360-point inspection. This ensures quality.

### Warranty

Kavak offers a warranty on all certified vehicles. The warranty covers major mechanical components.

## Return Policy

### 7-Day Return Guarantee

Kavak offers a 7-day return guarantee. If you're not satisfied, you can return the vehicle within 7 days.

## Delivery

### Home Delivery

Kavak offers home delivery service for your convenience.
"""  # noqa: E501

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        yield Path(f.name)
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


def test_retrieve_returns_relevant_chunks_for_guarantee_query(sample_knowledge_base):
    """Test that retrieval returns relevant chunks for guarantee query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("garantía", top_k=3)

    assert len(chunks) > 0
    # At least one chunk should have warranty/guarantee content
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_warranty_content = any("warranty" in text or "guarantee" in text for text in chunk_texts)
    assert has_warranty_content, f"Expected warranty/guarantee content in chunks: {chunk_texts}"
    # Top chunk should have positive score
    assert chunks[0].score >= 0


def test_retrieve_returns_relevant_chunks_for_inspection_query(sample_knowledge_base):
    """Test that retrieval returns relevant chunks for inspection query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("inspección", top_k=3)

    assert len(chunks) > 0
    # At least one chunk should have inspection content
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_inspection_content = any("inspection" in text for text in chunk_texts)
    assert has_inspection_content, f"Expected inspection content in chunks: {chunk_texts}"
    assert chunks[0].score >= 0


def test_retrieve_returns_relevant_chunks_for_delivery_query(sample_knowledge_base):
    """Test that retrieval returns relevant chunks for delivery query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    # Use "delivery" directly to match the English content in the fixture
    chunks = repo.retrieve("delivery", top_k=3)

    assert len(chunks) > 0
    # At least one chunk should have delivery content
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_delivery_content = any("delivery" in text for text in chunk_texts)
    assert has_delivery_content, f"Expected delivery content in chunks: {chunk_texts}"
    assert chunks[0].score >= 0


def test_retrieve_returns_chunks_sorted_by_score(sample_knowledge_base):
    """Test that retrieved chunks are sorted by score (highest first)."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("warranty guarantee", top_k=5)

    if len(chunks) > 1:
        # Scores should be in descending order
        for i in range(len(chunks) - 1):
            assert chunks[i].score >= chunks[i + 1].score


def test_retrieve_respects_top_k_limit(sample_knowledge_base):
    """Test that retrieve respects top_k limit."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("kavak", top_k=2)

    assert len(chunks) <= 2


def test_retrieve_handles_nonexistent_file():
    """Test that retrieve handles nonexistent file gracefully."""
    repo = LocalMarkdownKnowledgeBaseRepository("/nonexistent/path/file.md")
    chunks = repo.retrieve("test query", top_k=5)

    assert chunks == []


def test_retrieve_handles_empty_query(sample_knowledge_base):
    """Test that retrieve handles empty query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("", top_k=5)

    # Should return chunks but with low/zero scores
    assert isinstance(chunks, list)


def test_chunks_have_required_fields(sample_knowledge_base):
    """Test that retrieved chunks have all required fields."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("warranty", top_k=1)

    if chunks:
        chunk = chunks[0]
        assert chunk.id is not None
        assert chunk.text is not None
        assert chunk.score is not None
        assert chunk.source is not None
        assert isinstance(chunk.score, float)
        assert 0.0 <= chunk.score <= 1.0
