"""Answer FAQ with RAG use case."""

import re

from app.application.dtos.knowledge import KnowledgeChunk
from app.application.ports.knowledge_base_repository import KnowledgeBaseRepository


class AnswerFaqWithRag:
    """Use case for answering FAQ questions using RAG."""

    # Conservative threshold for minimum score to consider chunks relevant
    MIN_SCORE_THRESHOLD = 0.1

    # Safe fallback message in Spanish
    FALLBACK_MESSAGE = (
        "No tengo esa información con certeza en este momento. "
        "¿Quieres que te ayude con opciones de autos o con un estimado de financiamiento?"
    )

    def __init__(self, knowledge_base_repository: KnowledgeBaseRepository) -> None:
        """
        Initialize FAQ RAG use case.

        Args:
            knowledge_base_repository: Repository for knowledge base retrieval
        """
        self._knowledge_base_repository = knowledge_base_repository

    def execute(self, query: str) -> tuple[str, list[str]]:
        """
        Answer FAQ question using RAG.

        Args:
            query: User query

        Returns:
            Tuple of (reply, suggested_questions) - both in Spanish
        """
        # Retrieve relevant chunks
        chunks = self._knowledge_base_repository.retrieve(query, top_k=5)

        # Check if we have sufficient evidence
        if not chunks or (chunks and chunks[0].score < self.MIN_SCORE_THRESHOLD):
            return self._generate_fallback_response()

        # Generate answer from retrieved chunks
        reply = self._generate_answer(chunks)
        suggested_questions = self._generate_suggested_questions()

        return reply, suggested_questions

    def _generate_answer(self, chunks: list[KnowledgeChunk]) -> str:
        """
        Generate Spanish answer from retrieved chunks.

        Args:
            chunks: Retrieved knowledge chunks

        Returns:
            Spanish answer based on retrieved content
        """
        # Use top chunk for answer (most relevant)
        top_chunk = chunks[0]

        # Extract key information from chunk text
        # Simple approach: use the chunk text as base and format it in Spanish
        answer = self._format_chunk_as_answer(top_chunk.text)

        # If we have multiple relevant chunks, we can add supplementary info
        if len(chunks) > 1 and chunks[1].score >= self.MIN_SCORE_THRESHOLD:
            # Add context from second chunk if relevant
            supplementary = self._extract_key_point(chunks[1].text)
            if supplementary:
                answer += f"\n\nAdemás, {supplementary.lower()}"

        return answer

    def _format_chunk_as_answer(self, text: str) -> str:
        """
        Format chunk text as a Spanish answer.

        Args:
            text: Chunk text (already in Spanish from curated KB)

        Returns:
            Formatted Spanish answer using KB content directly
        """
        # The knowledge base is already in Spanish, so we use the content directly
        # Extract the most relevant information from the chunk
        # Remove markdown formatting and clean up the text

        # Remove markdown heading markers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        # Extract first paragraph or meaningful section (up to ~300 chars for concise answer)
        paragraphs = text.split("\n\n")
        if paragraphs:
            # Use first paragraph if it's reasonable length
            first_paragraph = paragraphs[0].strip()
            if len(first_paragraph) > 50 and len(first_paragraph) < 400:
                return first_paragraph

            # Otherwise, take first few sentences
            sentences = re.split(r"[.!?]\s+", text)
            answer_parts = []
            char_count = 0
            for sentence in sentences:
                if char_count + len(sentence) > 300:
                    break
                answer_parts.append(sentence.strip())
                char_count += len(sentence) + 2

            if answer_parts:
                answer = ". ".join(answer_parts)
                if not answer.endswith((".", "!", "?")):
                    answer += "."
                return answer

        # Fallback: return first 300 characters
        return text[:300].strip() + ("..." if len(text) > 300 else "")

    def _extract_key_point(self, text: str) -> str:
        """
        Extract a key point from chunk text for supplementary information.

        Args:
            text: Chunk text (in Spanish from curated KB)

        Returns:
            Key point in Spanish extracted from KB content, or empty string if none found
        """
        # Extract a concise key point from the Spanish KB content
        # Remove markdown and get first meaningful sentence
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = text.strip()

        # Get first sentence that's not too short
        sentences = re.split(r"[.!?]\s+", text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30:  # Meaningful length
                return sentence

        return ""

    def _generate_fallback_response(self) -> tuple[str, list[str]]:
        """
        Generate fallback response when no relevant chunks are found.

        Returns:
            Tuple of (fallback_message, suggested_questions) - both in Spanish
        """
        suggested_questions = [
            "¿Qué autos tienen disponibles?",
            "¿Cómo funciona el financiamiento?",
            "¿Qué garantías ofrecen?",
            "¿Puedo ver el auto antes de comprarlo?",
        ]

        return self.FALLBACK_MESSAGE, suggested_questions

    def _generate_suggested_questions(self) -> list[str]:
        """
        Generate suggested questions in Spanish.

        Returns:
            List of suggested questions
        """
        return [
            "¿Qué garantías ofrecen?",
            "¿Cómo funciona la entrega?",
            "¿Puedo financiar mi compra?",
            "¿Cómo es el proceso de inspección?",
        ]
