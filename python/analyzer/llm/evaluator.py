"""
Moduł oceny LLM — wysyła artykuł do modelu i parsuje strukturalną odpowiedź JSON.
Obsługuje błędy parsowania i zwraca bezpieczny wynik zastępczy w razie awarii.
"""
import json
import math
import re
import logging
from typing import Any

from .client import LLMClient
from .prompts import ARTICLE_EVALUATION_SYSTEM, ARTICLE_EVALUATION_USER

logger = logging.getLogger(__name__)

# Maksymalna liczba znaków treści przesyłanej do LLM
# (dłuższe artykuły są przycinane, by nie przekraczać limitu kontekstu)
MAX_CONTENT_CHARS = 9_000


class LLMEvaluator:
    """
    Ocenia artykuł pod kątem faktyczności, logiki i standardów dziennikarskich
    przy użyciu modelu językowego.
    """

    def __init__(self) -> None:
        self.client = LLMClient()

    # ------------------------------------------------------------------
    def evaluate(self, title: str, content: str) -> dict[str, Any]:
        """
        Główna metoda — zwraca słownik z wynikami i opisami.
        Nigdy nie rzuca wyjątku: w razie błędu zwraca wynik zastępczy.
        """
        truncated = content[:MAX_CONTENT_CHARS]
        if len(content) > MAX_CONTENT_CHARS:
            truncated += "\n\n[...tekst skrócony do analizy...]"

        prompt = ARTICLE_EVALUATION_USER.format(
            title=title or "(brak tytułu)",
            content=truncated,
        )

        try:
            # Limit obejmuje także tokeny rozumowania modelu, nie tylko odpowiedź JSON
            raw_text, tokens_used = self.client.complete(
                ARTICLE_EVALUATION_SYSTEM, prompt, max_tokens=16_000
            )
            result = self._parse(raw_text)
            result["tokens_used"] = tokens_used
            result["model"]       = self.client.model
            result["success"]     = True
            return result

        except Exception as exc:
            logger.error(f"LLM evaluation failed: {exc}", exc_info=True)
            return self._fallback(str(exc))

    # ------------------------------------------------------------------
    def _parse(self, raw: str) -> dict[str, Any]:
        """Wyodrębnia i parsuje JSON z odpowiedzi LLM."""
        # LLM może zwrócić JSON z dodatkowym tekstem — wycinamy blok JSON
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise ValueError(f"Brak bloku JSON w odpowiedzi LLM: {raw[:200]}")

        data = json.loads(json_match.group())

        def section(name: str) -> dict:
            value = data.get(name)
            if not isinstance(value, dict):
                raise ValueError(f"Brak sekcji '{name}' w odpowiedzi LLM")
            return value

        def score(name: str, part: dict) -> float:
            # Brakującego wyniku nie zastępujemy domyślnym 50: taki sztuczny wynik
            # trafiłby do bazy jako 'done'. Wyjątek kończy się fallbackiem i ponowieniem.
            if "score" not in part:
                raise ValueError(f"Brak wyniku '{name}.score' w odpowiedzi LLM")
            val = float(part["score"])
            if not math.isfinite(val):
                raise ValueError(f"Niepoprawny wynik '{name}.score': {part['score']!r}")
            return max(0.0, min(100.0, val))

        factuality = section("factuality")
        logic      = section("logic")
        journalism = section("journalism")

        return {
            "factuality_score":       score("factuality", factuality),
            "factuality_description": factuality.get("description", ""),
            "factuality_flags":       factuality.get("flags", {}),

            "logic_score":            score("logic", logic),
            "logic_description":      logic.get("description", ""),
            "logic_flags":            logic.get("flags", {}),

            "journalism_score":       score("journalism", journalism),
            "journalism_description": journalism.get("description", ""),
            "journalism_flags":       journalism.get("flags", {}),

            "overall_description":    data.get("overall_description", ""),
        }

    # ------------------------------------------------------------------
    def _fallback(self, error: str) -> dict[str, Any]:
        msg = "Analiza LLM zakończyła się błędem — wyniki orientacyjne."
        return {
            "factuality_score":       50.0,
            "factuality_description": msg,
            "factuality_flags":       {},
            "logic_score":            50.0,
            "logic_description":      msg,
            "logic_flags":            {},
            "journalism_score":       50.0,
            "journalism_description": msg,
            "journalism_flags":       {},
            "overall_description":    f"{msg} Błąd: {error}",
            "tokens_used":            0,
            "model":                  "unknown",
            "success":                False,
            "error":                  error,
        }
