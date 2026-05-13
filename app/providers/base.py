from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict]) -> tuple[str, int]:
        """Send messages, return (reply, tokens_used). Used by ChatService."""
        ...

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> tuple[str, int, int, int]:
        """
        Single-turn call with explicit system prompt.
        Returns (reply, cache_creation_tokens, cache_read_tokens, total_tokens).
        For providers without native caching, cache_creation_tokens=0.
        """
        ...
