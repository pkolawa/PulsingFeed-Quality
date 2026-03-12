"""
Analiza deterministyczna — poprawność językowa.

Używa wyłącznie wyrażeń regularnych i statystyk tekstu do oceny jakości
językowej artykułu. Wynik (0–100) oparty na interpunkcji, długości zdań
i spójności tekstu.
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Wzorce interpunkcyjne ────────────────────────────────────────────
_RE_MISSING_SPACE_AFTER = re.compile(r"[,;:](?!\s|$)")
_RE_SPACE_BEFORE_PUNCT  = re.compile(r"\s+[,;:.!?]")
_RE_DOUBLE_SPACE        = re.compile(r" {2,}")
_RE_REPEATED_PUNCT      = re.compile(r"[!?]{3,}")
_RE_ELLIPSIS_WRONG      = re.compile(r"\.{2}(?!\.)")   # dwie kropki (nie wielokropek)

# ── Wzorce potencjalnych błędów ortograficznych ───────────────────────
# Małe litery po kropce/wykrzykniku/pytajniku (poza skrótami)
_RE_LOWERCASE_AFTER_SENT = re.compile(r"(?<=[.!?])\s+[a-z]")
# Brak spacji po przecinku (ale nie w liczbach)
_RE_COMMA_NO_SPACE      = re.compile(r",(?!\s|\d)")


class LinguisticAnalyzer:
    """Analizuje poprawność językową tekstu w języku polskim."""

    def __init__(self) -> None:
        logger.info("Inicjalizacja analizatora językowego (regex + statystyki).")

    # ------------------------------------------------------------------
    def analyze(self, content: str, title: str = "") -> dict[str, Any]:
        full_text = f"{title}\n{content}" if title else content
        full_text = full_text.strip()

        if not full_text:
            return self._empty_result()

        words = full_text.split()
        word_count = len(words)

        # ── Błędy interpunkcyjne ─────────────────────────────────────
        punctuation_errors = (
            len(_RE_MISSING_SPACE_AFTER.findall(full_text))
            + len(_RE_SPACE_BEFORE_PUNCT.findall(full_text))
            + len(_RE_DOUBLE_SPACE.findall(full_text))
            + len(_RE_REPEATED_PUNCT.findall(full_text))
            + len(_RE_ELLIPSIS_WRONG.findall(full_text))
            + len(_RE_COMMA_NO_SPACE.findall(full_text))
        )

        # ── Sygnały ortograficzne (heurystyki) ───────────────────────
        spelling_signals = len(_RE_LOWERCASE_AFTER_SENT.findall(full_text))

        total_errors    = punctuation_errors + spelling_signals
        errors_per_1000 = (total_errors / word_count) * 1000 if word_count else 0.0

        # ── Statystyki zdań ──────────────────────────────────────────
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        sentences = [s.strip() for s in sentences if len(s.strip().split()) > 1]
        sentence_count   = max(len(sentences), 1)
        avg_sentence_len = word_count / sentence_count

        # ── Wynik bazowy ─────────────────────────────────────────────
        base_score = max(10.0, 100.0 - errors_per_1000 * 6.0)

        # ── Korekta czytelności ──────────────────────────────────────
        if 15 <= avg_sentence_len <= 25:
            readability_adj = +5.0
        elif avg_sentence_len > 40:
            readability_adj = -10.0
        elif avg_sentence_len < 7:
            readability_adj = -5.0
        else:
            readability_adj = 0.0

        linguistic_score = min(100.0, max(0.0, base_score + readability_adj))

        return {
            "score":                  round(linguistic_score, 2),
            "word_count":             word_count,
            "total_errors":           total_errors,
            "grammar_errors":         0,
            "spelling_errors":        spelling_signals,
            "punctuation_errors":     punctuation_errors,
            "errors_per_1000_words":  round(errors_per_1000, 2),
            "avg_sentence_length":    round(avg_sentence_len, 1),
            "sentence_count":         sentence_count,
            "description":            self._build_description(
                total_errors, word_count, errors_per_1000,
                spelling_signals, punctuation_errors, avg_sentence_len,
            ),
        }

    # ------------------------------------------------------------------
    def _build_description(
        self,
        total: int, words: int, per_1000: float,
        spelling: int, punctuation: int,
        avg_sent: float,
    ) -> str:
        parts: list[str] = []

        if per_1000 < 1:
            parts.append("Tekst napisany poprawnie językowo — wykryto śladowe błędy lub ich brak.")
        elif per_1000 < 5:
            parts.append(
                f"Tekst zawiera niewielką liczbę uchybień językowych "
                f"({total} na {words} słów, {per_1000:.1f}/1 000)."
            )
        elif per_1000 < 15:
            parts.append(
                f"Wykryto zauważalną liczbę błędów językowych "
                f"({total} na {words} słów, {per_1000:.1f}/1 000)."
            )
        else:
            parts.append(
                f"Tekst zawiera znaczną liczbę błędów językowych "
                f"({total} na {words} słów, {per_1000:.1f}/1 000), "
                f"co istotnie obniża jakość artykułu."
            )

        details: list[str] = []
        if spelling > 0:
            details.append(f"{spelling} ortograficznych (heurystyka)")
        if punctuation > 0:
            details.append(f"{punctuation} interpunkcyjnych")
        if details:
            parts.append(f"Typy błędów: {', '.join(details)}.")

        if avg_sent > 40:
            parts.append(
                f"Zdania są bardzo długie (śr. {avg_sent:.0f} słów) — "
                f"tekst może być trudny w odbiorze."
            )
        elif avg_sent < 7:
            parts.append(
                f"Zdania są bardzo krótkie (śr. {avg_sent:.0f} słów) — "
                f"styl może sprawiać wrażenie urwanego."
            )
        else:
            parts.append(f"Długość zdań jest odpowiednia (śr. {avg_sent:.0f} słów).")

        return " ".join(parts)

    # ------------------------------------------------------------------
    def _empty_result(self) -> dict[str, Any]:
        return {
            "score": 0.0, "word_count": 0, "total_errors": 0,
            "grammar_errors": 0, "spelling_errors": 0, "punctuation_errors": 0,
            "errors_per_1000_words": 0.0, "avg_sentence_length": 0.0,
            "sentence_count": 0, "description": "Brak treści do analizy.",
        }

    def close(self) -> None:
        pass
