"""
Klient Anthropic API — opakowanie dla wywołań LLM.
"""
import logging
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)


class LLMClient:
    """Cienka warstwa nad biblioteką anthropic."""

    def __init__(self) -> None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("Brak ANTHROPIC_API_KEY w zmiennych środowiskowych.")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model  = LLM_MODEL

    def complete(self, prompt: str, max_tokens: int = 1_500) -> tuple[str, int]:
        """
        Wysyła prompt do LLM i zwraca (tekst_odpowiedzi, łączna_liczba_tokenów).
        """
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text        = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens
        logger.debug(f"LLM odpowiedział — tokeny: {tokens_used}")
        return text, tokens_used
