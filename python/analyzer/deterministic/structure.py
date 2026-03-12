"""
Analiza deterministyczna — struktura artykułu.

Ocenia długość tekstu, podział na akapity i jakość nagłówka.
Wynik (0–100) wchodzi jako składnik oceny poprawności językowej.
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Progi długości artykułu (w słowach)
MIN_WORDS_SHORT     = 100
MIN_WORDS_ADEQUATE  = 300
MIN_WORDS_GOOD      = 500
MAX_WORDS_OPTIMAL   = 2_500


class StructureAnalyzer:
    """Analizuje strukturę artykułu (długość, akapity, nagłówek)."""

    def analyze(self, content: str, title: str = "") -> dict[str, Any]:
        word_count = len(content.split())

        # --- Akapity ---
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", content) if p.strip()]
        if len(paragraphs) <= 1:
            # fallback: pojedyncze nowe linie
            paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        paragraph_count   = max(len(paragraphs), 1)
        avg_para_len      = word_count / paragraph_count

        # --- Wynik: długość artykułu ---
        if word_count < MIN_WORDS_SHORT:
            length_score = 15.0
        elif word_count < MIN_WORDS_ADEQUATE:
            length_score = 40.0 + (word_count - MIN_WORDS_SHORT) / (MIN_WORDS_ADEQUATE - MIN_WORDS_SHORT) * 30.0
        elif word_count < MIN_WORDS_GOOD:
            length_score = 70.0 + (word_count - MIN_WORDS_ADEQUATE) / (MIN_WORDS_GOOD - MIN_WORDS_ADEQUATE) * 30.0
        elif word_count <= MAX_WORDS_OPTIMAL:
            length_score = 100.0
        else:
            # Artykuły bardzo długie — minimalna kara
            length_score = max(85.0, 100.0 - (word_count - MAX_WORDS_OPTIMAL) / 1_000 * 3.0)

        # --- Wynik: podział na akapity ---
        if paragraph_count == 1:
            structure_score = 45.0
        elif paragraph_count == 2:
            structure_score = 65.0
        elif paragraph_count <= 4:
            structure_score = 80.0
        else:
            structure_score = 100.0

        # --- Wynik: nagłówek ---
        headline_score = self._score_headline(title) if title else 70.0

        # --- Wynik łączny struktury ---
        combined = (
            length_score    * 0.50 +
            structure_score * 0.30 +
            headline_score  * 0.20
        )

        return {
            "score":             round(combined, 2),
            "word_count":        word_count,
            "paragraph_count":   paragraph_count,
            "avg_para_length":   round(avg_para_len, 1),
            "length_score":      round(length_score, 2),
            "structure_score":   round(structure_score, 2),
            "headline_score":    round(headline_score, 2),
            "description":       self._build_description(
                word_count, paragraph_count, avg_para_len, headline_score
            ),
        }

    # ------------------------------------------------------------------
    def _score_headline(self, title: str) -> float:
        score = 100.0
        words = title.split()

        if len(words) < 3:
            score -= 20.0   # Nagłówek zbyt krótki
        if len(words) > 16:
            score -= 10.0   # Nagłówek zbyt długi

        if title.isupper():
            score -= 35.0   # Nagłówek w całości wielkimi literami

        exclamations = title.count("!")
        if exclamations >= 2:
            score -= 30.0
        elif exclamations == 1:
            score -= 12.0

        questions = title.count("?")
        if questions > 1:
            score -= 15.0

        # Nadmierne użycie wielkich liter w środku tytułu (poza pierwszym słowem)
        caps_mid = sum(1 for w in words[1:] if w.isupper() and len(w) > 2)
        if caps_mid >= 2:
            score -= 20.0

        return max(0.0, score)

    # ------------------------------------------------------------------
    def _build_description(
        self,
        word_count: int,
        paragraph_count: int,
        avg_para_len: float,
        headline_score: float,
    ) -> str:
        parts: list[str] = []

        if word_count < MIN_WORDS_SHORT:
            parts.append(f"Artykuł jest bardzo krótki ({word_count} słów) — temat nie jest wyczerpująco omówiony.")
        elif word_count < MIN_WORDS_ADEQUATE:
            parts.append(f"Artykuł jest stosunkowo krótki ({word_count} słów).")
        elif word_count <= MAX_WORDS_OPTIMAL:
            parts.append(f"Artykuł ma odpowiednią długość ({word_count} słów).")
        else:
            parts.append(f"Artykuł jest bardzo długi ({word_count} słów).")

        if paragraph_count == 1:
            parts.append("Tekst stanowi jeden niepodzielony blok — brak podziału na akapity utrudnia czytanie.")
        elif paragraph_count <= 2:
            parts.append("Artykuł ma słaby podział na akapity (tylko 2).")
        else:
            parts.append(f"Artykuł ma dobrą strukturę ({paragraph_count} akapitów, śr. {avg_para_len:.0f} słów/akapit).")

        if headline_score < 60:
            parts.append("Nagłówek wykazuje cechy sensacjonalizmu lub ma nieodpowiedni format.")
        elif headline_score >= 90:
            parts.append("Nagłówek sformułowany poprawnie i rzetelnie.")

        return " ".join(parts)
