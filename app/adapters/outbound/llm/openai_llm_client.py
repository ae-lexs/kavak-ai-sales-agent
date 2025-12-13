"""OpenAI LLM client adapter."""

from typing import Optional

from openai import OpenAI

from app.application.ports.llm_client import LLMClient
from app.infrastructure.config.settings import settings


class OpenAILLMClient(LLMClient):
    """OpenAI LLM client implementation using official SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """
        Initialize OpenAI LLM client.

        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: Model name (defaults to settings.openai_model)
            timeout_seconds: Request timeout in seconds (defaults to settings.openai_timeout_seconds)
        """
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.openai_model
        self._timeout = timeout_seconds or settings.openai_timeout_seconds

        if not self._api_key:
            raise ValueError("OpenAI API key is required")

        # Use timeout as float (seconds) for compatibility
        # OpenAI SDK v1.x accepts float timeout
        self._client = OpenAI(
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=1,  # Minimal retry for deterministic behavior
        )

    def generate_reply(self, system_prompt: str, user_message: str, context: dict) -> str:
        """
        Generate a reply using OpenAI API.

        Args:
            system_prompt: System prompt to guide LLM behavior
            user_message: User message/query
            context: Additional context dictionary (e.g., retrieved chunks)

        Returns:
            Generated reply in Spanish

        Raises:
            Exception: If LLM call fails or returns empty response
        """
        # Build messages with strict Spanish enforcement
        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\nIMPORTANT: You must respond ONLY in Spanish. Never use English or any other language.",
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,  # Balance between creativity and consistency
                max_tokens=500,  # Limit response length
            )

            # Extract reply from response
            if not response.choices or response.choices[0].message.content is None:
                raise ValueError("Empty response from OpenAI API")

            reply = response.choices[0].message.content.strip()

            if not reply:
                raise ValueError("Empty reply from OpenAI API")

            return reply

        except Exception as e:
            # Re-raise to allow fallback handling at use case level
            raise Exception(f"OpenAI API call failed: {str(e)}") from e
