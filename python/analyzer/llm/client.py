"""
Klient LLM — obsługuje Anthropic i OpenAI.
Aktywny dostawca wybierany jest przez zmienną LLM_PROVIDER w pliku .env.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from config import LLM_PROVIDER, LLM_MODEL, ANTHROPIC_API_KEY, ANTHROPIC_EFFORT, OPENAI_API_KEY

logger = logging.getLogger(__name__)


class _BaseProvider(ABC):
    """Wspólny interfejs dla wszystkich dostawców LLM."""

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(self, system: str, prompt: str, max_tokens: int) -> tuple[str, int]:
        """
        Zwraca (tekst_odpowiedzi, łączna_liczba_tokenów).
        `system` to stała instrukcja (cache'owana), `prompt` — treść zmienna.
        """


class _AnthropicProvider(_BaseProvider):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        if not ANTHROPIC_API_KEY:
            raise ValueError("Brak ANTHROPIC_API_KEY w zmiennych środowiskowych.")
        import anthropic
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def complete(self, system: str, prompt: str, max_tokens: int) -> tuple[str, int]:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            # Prompt caching: stała instrukcja systemowa jest cache'owana (TTL 5 min),
            # kolejne artykuły z partii płacą ~10% ceny za te tokeny wejściowe
            system=[{
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
            # extra_body — działa także na starszych wersjach SDK bez parametru output_config
            extra_body={"output_config": {"effort": ANTHROPIC_EFFORT}},
        )
        # Model może odmówić odpowiedzi (HTTP 200 + stop_reason "refusal")
        if message.stop_reason == "refusal":
            raise ValueError(f"Model odmówił odpowiedzi: {getattr(message, 'stop_details', None)}")
        if message.stop_reason == "max_tokens":
            raise ValueError(f"Odpowiedź ucięta po {max_tokens} tokenach (max_tokens).")

        # Odpowiedź może zaczynać się od bloków "thinking" — bierzemy tylko bloki tekstowe
        text = "".join(block.text for block in message.content if block.type == "text")

        # input_tokens nie obejmuje tokenów z cache — sumujemy wszystkie składniki
        usage = message.usage
        cache_write = getattr(usage, "cache_creation_input_tokens", None) or 0
        cache_read  = getattr(usage, "cache_read_input_tokens", None) or 0
        logger.debug(
            f"Anthropic usage — input: {usage.input_tokens}, cache_write: {cache_write}, "
            f"cache_read: {cache_read}, output: {usage.output_tokens}"
        )
        tokens_used = usage.input_tokens + cache_write + cache_read + usage.output_tokens
        return text, tokens_used


class _OpenAIProvider(_BaseProvider):
    def __init__(self, model: str) -> None:
        super().__init__(model)
        if not OPENAI_API_KEY:
            raise ValueError("Brak OPENAI_API_KEY w zmiennych środowiskowych.")
        from openai import OpenAI
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def complete(self, system: str, prompt: str, max_tokens: int) -> tuple[str, int]:
        # OpenAI cache'uje wspólny prefiks automatycznie — wystarczy stała wiadomość systemowa na początku
        response = self._client.chat.completions.create(
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
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

    def complete(self, system: str, prompt: str, max_tokens: int = 1_500) -> tuple[str, int]:
        """
        Wysyła prompt do LLM i zwraca (tekst_odpowiedzi, łączna_liczba_tokenów).
        `system` powinien być stały między wywołaniami — jest cache'owany.
        """
        text, tokens_used = self._provider.complete(system, prompt, max_tokens)
        logger.debug(f"LLM odpowiedział — tokeny: {tokens_used}")
        return text, tokens_used
