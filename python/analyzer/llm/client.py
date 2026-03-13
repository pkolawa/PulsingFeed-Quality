"""
Klient LLM — obsługuje Anthropic i OpenAI.
Aktywny dostawca wybierany jest przez zmienną LLM_PROVIDER w pliku .env.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from config import LLM_PROVIDER, LLM_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


class _BaseProvider(ABC):
    """Wspólny interfejs dla wszystkich dostawców LLM."""

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int) -> tuple[str, int]:
        """Zwraca (tekst_odpowiedzi, łączna_liczba_tokenów)."""


class _AnthropicProvider(_BaseProvider):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        if not ANTHROPIC_API_KEY:
            raise ValueError("Brak ANTHROPIC_API_KEY w zmiennych środowiskowych.")
        import anthropic
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def complete(self, prompt: str, max_tokens: int) -> tuple[str, int]:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens
        return text, tokens_used


class _OpenAIProvider(_BaseProvider):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        if not OPENAI_API_KEY:
            raise ValueError("Brak OPENAI_API_KEY w zmiennych środowiskowych.")
        from openai import OpenAI
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def complete(self, prompt: str, max_tokens: int) -> tuple[str, int]:
        response = self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
        if not text:
            # Modele rozumujące (o1, o3, gpt-5-nano itp.) mogą zwracać None w polu
            # content gdy treść trafia do pola reasoning_content — logujemy to wyraźnie.
            raw = response.choices[0].message.model_dump()
            raise ValueError(
                f"OpenAI zwrócił pustą treść (content=None). "
                f"Pola wiadomości: {list(raw.keys())}. "
                f"Rozważ użycie modelu nierozumującego (np. gpt-4o-mini)."
            )
        tokens_used = response.usage.total_tokens
        return text, tokens_used


_PROVIDERS: dict[str, type[_BaseProvider]] = {
    "anthropic": _AnthropicProvider,
    "openai":    _OpenAIProvider,
}


class LLMClient:
    """Fasada — deleguje wywołania do aktywnego dostawcy."""

    def __init__(self) -> None:
        provider_cls = _PROVIDERS.get(LLM_PROVIDER)
        if provider_cls is None:
            raise ValueError(
                f"Nieznany LLM_PROVIDER: '{LLM_PROVIDER}'. "
                f"Dostępne wartości: {', '.join(_PROVIDERS)}"
            )
        self._provider = provider_cls(LLM_MODEL)
        self.model = self._provider.model
        logger.info(f"Używany dostawca LLM: {LLM_PROVIDER} / {self.model}")

    def complete(self, prompt: str, max_tokens: int = 1_500) -> tuple[str, int]:
        """
        Wysyła prompt do LLM i zwraca (tekst_odpowiedzi, łączna_liczba_tokenów).
        """
        text, tokens_used = self._provider.complete(prompt, max_tokens)
        logger.debug(f"LLM odpowiedział — tokeny: {tokens_used}")
        return text, tokens_used
