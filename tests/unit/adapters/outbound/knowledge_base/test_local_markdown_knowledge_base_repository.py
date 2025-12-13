"""Unit tests for LocalMarkdownKnowledgeBaseRepository."""

import tempfile
from pathlib import Path

import pytest

from app.adapters.outbound.knowledge_base.local_markdown_knowledge_base_repository import (
    LocalMarkdownKnowledgeBaseRepository,
)


@pytest.fixture
def sample_knowledge_base():
    """Create a temporary knowledge base file for testing using Spanish content."""
    content = """# Kavak México – Knowledge Base

## 2. Presencia Nacional

Actualmente, Kavak cuenta con **15 sedes** y **13 centros de inspección**, cubriendo las principales ciudades del país.

### 2.1 Puebla

**Kavak Explanada**
Calle Ignacio Allende 512, Santiago Momoxpan, Puebla, 72760
Horario: Lunes a Domingo, 9:00 a.m. – 6:00 p.m.

## 4. Autos 100% Certificados

Todos los autos pasan por una **inspección integral** realizada por especialistas, que evalúan:

* Exterior.
* Interior.
* Motor y componentes mecánicos.

Esto garantiza el estándar de calidad del sello **Kavak**.

## 8. Periodo de Prueba y Garantía

* **7 días o 300 km** de prueba.
* Devolución garantizada si el auto no convence.
* **Garantía de 3 meses**, con opción de extender hasta 1 año.
"""  # noqa: E501

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
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
    # At least one chunk should have warranty/guarantee content (in Spanish)
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_warranty_content = any("garantía" in text or "garantia" in text for text in chunk_texts)
    assert has_warranty_content, f"Expected garantía content in chunks: {chunk_texts}"
    # Top chunk should have positive score
    assert chunks[0].score >= 0


def test_retrieve_returns_relevant_chunks_for_inspection_query(sample_knowledge_base):
    """Test that retrieval returns relevant chunks for inspection query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("inspección", top_k=3)

    assert len(chunks) > 0
    # At least one chunk should have inspection content (in Spanish)
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_inspection_content = any(
        "inspección" in text or "inspeccion" in text for text in chunk_texts
    )
    assert has_inspection_content, f"Expected inspección content in chunks: {chunk_texts}"
    assert chunks[0].score >= 0


def test_retrieve_returns_relevant_chunks_for_sedes_query(sample_knowledge_base):
    """Test that retrieval returns relevant chunks for sedes/location query."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("sedes", top_k=3)

    assert len(chunks) > 0
    # At least one chunk should have sedes/location content (in Spanish)
    chunk_texts = [chunk.text.lower() for chunk in chunks]
    has_sedes_content = any(
        "sedes" in text or "puebla" in text or "ubicación" in text for text in chunk_texts
    )
    assert has_sedes_content, f"Expected sedes content in chunks: {chunk_texts}"
    assert chunks[0].score >= 0


def test_retrieve_returns_chunks_sorted_by_score(sample_knowledge_base):
    """Test that retrieved chunks are sorted by score (highest first)."""
    repo = LocalMarkdownKnowledgeBaseRepository(str(sample_knowledge_base))
    chunks = repo.retrieve("garantía", top_k=5)

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
    chunks = repo.retrieve("garantía", top_k=1)

    if chunks:
        chunk = chunks[0]
        assert chunk.id is not None
        assert chunk.text is not None
        assert chunk.score is not None
        assert chunk.source is not None
        assert isinstance(chunk.score, float)
        assert 0.0 <= chunk.score <= 1.0


def test_retrieve_sedes_from_curated_kb():
    """Test that sedes queries retrieve chunks from the actual curated knowledge base."""
    # Use the actual curated KB file
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent.parent.parent.parent
    kb_path = project_root / "data" / "knowledge_base.md"

    if not kb_path.exists():
        pytest.skip("Curated knowledge base file not found")

    repo = LocalMarkdownKnowledgeBaseRepository(str(kb_path))

    # Test various sedes-related queries
    for query in ["sedes", "ubicación", "centros kavak", "dónde están", "puebla", "monterrey"]:
        chunks = repo.retrieve(query, top_k=5)
        assert len(chunks) > 0, f"Query '{query}' should return at least one chunk"
        # Verify chunks contain Spanish content about locations
        chunk_texts = " ".join([chunk.text.lower() for chunk in chunks])
        assert (
            "sedes" in chunk_texts
            or "puebla" in chunk_texts
            or "monterrey" in chunk_texts
            or "ciudad" in chunk_texts
        ), f"Query '{query}' should return chunks about locations/sedes"
