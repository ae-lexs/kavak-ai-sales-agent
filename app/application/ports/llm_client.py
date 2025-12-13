"""LLM client port interface."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Port interface for LLM client."""

    @abstractmethod
    def generate_reply(self, system_prompt: str, user_message: str, context: dict) -> str:
        """
        Generate a reply using the LLM.

        Args:
            system_prompt: System prompt to guide LLM behavior
            user_message: User message/query
            context: Additional context dictionary (e.g., retrieved chunks)

        Returns:
            Generated reply in Spanish

        Raises:
            Exception: If LLM call fails or returns empty response
        """
        pass
