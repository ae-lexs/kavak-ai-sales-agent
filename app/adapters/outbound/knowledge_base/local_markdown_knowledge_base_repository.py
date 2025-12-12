"""Local markdown knowledge base repository implementation."""

import re
from pathlib import Path
from typing import Optional
from unicodedata import normalize

from app.application.dtos.knowledge import KnowledgeChunk
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository


class LocalMarkdownKnowledgeBaseRepository(KnowledgeBaseRepository):
    """Local markdown knowledge base repository with deterministic retrieval."""

    def __init__(self, knowledge_base_path: Optional[str] = None) -> None:
        """
        Initialize local markdown knowledge base repository.

        Args:
            knowledge_base_path: Path to knowledge base markdown file.
                                Defaults to data/knowledge_base.md relative to project root.
        """
        if knowledge_base_path is None:
            # Default to data/knowledge_base.md relative to project root
            project_root = Path(__file__).parent.parent.parent.parent.parent
            knowledge_base_path = str(project_root / "data" / "knowledge_base.md")

        self._knowledge_base_path = Path(knowledge_base_path)
        self._chunks: Optional[list[KnowledgeChunk]] = None

    def retrieve(self, query: str, top_k: int = 5) -> list[KnowledgeChunk]:
        """
        Retrieve relevant knowledge chunks for a query.

        Args:
            query: Search query
            top_k: Maximum number of chunks to return

        Returns:
            List of knowledge chunks sorted by relevance score (highest first)
        """
        # Load and chunk knowledge base if not already loaded
        if self._chunks is None:
            self._chunks = self._load_and_chunk()

        # Normalize query
        query_tokens = self._normalize_text(query)

        # Score each chunk
        scored_chunks = []
        for chunk in self._chunks:
            score = self._calculate_score(chunk.text, query_tokens)
            scored_chunks.append(
                KnowledgeChunk(
                    id=chunk.id,
                    text=chunk.text,
                    score=score,
                    source=chunk.source,
                )
            )

        # Sort by score (highest first) and return top_k
        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks[:top_k]

    def _load_and_chunk(self) -> list[KnowledgeChunk]:
        """
        Load knowledge base markdown file and chunk by headings.

        Returns:
            List of knowledge chunks
        """
        if not self._knowledge_base_path.exists():
            return []

        content = self._knowledge_base_path.read_text(encoding="utf-8")
        chunks = []

        # Split by headings (# and ##)
        # Pattern to match headings and content
        heading_pattern = r"^(#{1,2})\s+(.+)$"

        current_heading: Optional[str] = None
        current_content: list[str] = []
        chunk_id = 0

        lines = content.split("\n")
        for line in lines:
            heading_match = re.match(heading_pattern, line)
            if heading_match:
                # Save previous chunk if exists
                if current_heading and current_content:
                    chunk_text = "\n".join(current_content).strip()
                    if chunk_text:
                        chunks.append(
                            KnowledgeChunk(
                                id=f"chunk_{chunk_id}",
                                text=chunk_text,
                                score=0.0,  # Will be calculated during retrieval
                                source=self._knowledge_base_path.name,
                            )
                        )
                        chunk_id += 1

                # Start new chunk
                current_heading = heading_match.group(2).strip()
                current_content = [line]  # Include heading in chunk
            else:
                # Add line to current chunk
                if line.strip() or current_content:  # Include empty lines if we have content
                    current_content.append(line)

        # Save last chunk
        if current_heading and current_content:
            chunk_text = "\n".join(current_content).strip()
            if chunk_text:
                chunks.append(
                    KnowledgeChunk(
                        id=f"chunk_{chunk_id}",
                        text=chunk_text,
                        score=0.0,
                        source=self._knowledge_base_path.name,
                    )
                )

        return chunks

    def _normalize_text(self, text: str) -> list[str]:
        """
        Normalize text for tokenization: lowercase, remove accents, split into tokens.

        Args:
            text: Input text

        Returns:
            List of normalized tokens
        """
        # Convert to lowercase
        text_lower = text.lower()

        # Remove accents (normalize to NFD and remove combining characters)
        text_no_accents = normalize("NFD", text_lower)
        text_no_accents = "".join(
            char for char in text_no_accents if not (0x0300 <= ord(char) <= 0x036F)
        )

        # Split into tokens (words)
        # Remove punctuation and split by whitespace
        tokens = re.findall(r"\b\w+\b", text_no_accents)

        return tokens

    def _calculate_score(self, chunk_text: str, query_tokens: list[str]) -> float:
        """
        Calculate relevance score using token overlap (deterministic).

        Args:
            chunk_text: Chunk text to score
            query_tokens: Normalized query tokens

        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not query_tokens:
            return 0.0

        # Normalize chunk text
        chunk_tokens = self._normalize_text(chunk_text)

        if not chunk_tokens:
            return 0.0

        # Count matching tokens
        chunk_token_set = set(chunk_tokens)
        query_token_set = set(query_tokens)

        # Calculate intersection
        matching_tokens = chunk_token_set.intersection(query_token_set)

        if not matching_tokens:
            return 0.0

        # Score based on:
        # 1. Ratio of matching tokens to query tokens (precision)
        # 2. Ratio of matching tokens to chunk tokens (recall-like)
        # Use a simple average for deterministic scoring
        precision = len(matching_tokens) / len(query_token_set)
        recall_like = len(matching_tokens) / len(chunk_token_set)

        # Weighted average (favor precision slightly)
        score = (0.6 * precision) + (0.4 * recall_like)

        # Normalize to 0.0-1.0 range (should already be in range, but ensure)
        return min(1.0, max(0.0, score))
