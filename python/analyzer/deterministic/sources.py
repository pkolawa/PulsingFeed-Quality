"""
Analiza deterministyczna — rzetelność i obecność źródeł.

Wykrywa linki, cytaty oraz frazeologię atrybucyjną (powiedział, według, itp.).
Wynik (0–100) odzwierciedla stopień oparcia artykułu na weryfikowalnych źródłach.
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# --- Wzorce wykrywania źródeł ---

URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

QUOTE_RE = re.compile(
    r'[„"«\u201e\u201c\u00ab]'       # otwierający cudzysłów
    r'([^„"»\u201d\u00bb]{10,200})'  # treść cytatu (10–200 znaków)
    r'["\u201d»\u00bb]',             # zamykający cudzysłów
)

# Polskie wyrażenia atrybucyjne — słowa przypisania do osoby / instytucji
ATTRIBUTION_PATTERNS: list[str] = [
    # Czasowniki wypowiedzi
    r"\b(?:powiedział|powiedziano|powiedziała|stwierdzili?a?|oświadczyli?a?|"
    r"poinformował[ao]?|przekazali?a?|zaznaczyli?a?|wyjaśnili?a?|"
    r"zapowiedział[ao]?|potwierdził[ao]?|dodał[ao]?|podkreślili?a?|"
    r"zaznaczył[ao]?|twierdzi|twierdzą|zaapelował[ao]?|ocenili?a?)\b",
    # Wyrażenia przyimkowe
    r"\bwedług\s+\w+",
    r"\bzda(?:niem|nie)\s+\w+",
    r"\bw\s+ocenie\s+\w+",
    r"\bjak\s+(?:podaje|informuje|twierdzi|mówi|wynika\s+z)\s+\w+",
    r"\bcytuje\s+\w+",
    r"\b(?:rzecznik|ekspert|specjalist[aę]|analityk|minister|prezes|dyrektor|"
    r"szef|kierownik|profesor|dr\b|doktor)\b",
    r"\b(?:źródła?|informator[zy]?)\s+\w+",
    r"\bpodano\s+w\b",
    r"\bza\s+(?:PAP|Reuters|AFP|AP|IAR)\b",
]

ATTR_COMPILED = [re.compile(p, re.IGNORECASE) for p in ATTRIBUTION_PATTERNS]


class SourcesAnalyzer:
    """Ocenia obecność i różnorodność źródeł w artykule."""

    def analyze(self, content: str) -> dict[str, Any]:
        word_count = max(len(content.split()), 1)

        # --- Linki zewnętrzne ---
        urls = URL_RE.findall(content)
        url_count = len(urls)

        # --- Cytaty bezpośrednie ---
        quotes = QUOTE_RE.findall(content)
        quote_count = len(quotes)

        # --- Wyrażenia atrybucyjne ---
        attr_spans: set[int] = set()
        for pattern in ATTR_COMPILED:
            for m in pattern.finditer(content):
                attr_spans.add(m.start() // 50)  # grupujemy bliskie trafienia
        attribution_count = len(attr_spans)

        # --- Punktacja ---
        score = 0.0

        # Linki: do 25 pkt (każdy link +12, max 2 linki)
        score += min(25.0, url_count * 12.0)

        # Cytaty: do 35 pkt
        score += min(35.0, quote_count * 12.0)

        # Atrybucje: do 40 pkt
        score += min(40.0, attribution_count * 8.0)

        # Artykuł bez żadnych źródeł
        if url_count == 0 and quote_count == 0 and attribution_count == 0:
            # Krótkie newsy mają więcej wyrozumiałości
            score = 20.0 if word_count < 200 else 5.0

        score = min(100.0, score)

        return {
            "score":              round(score, 2),
            "url_count":          url_count,
            "quote_count":        quote_count,
            "attribution_count":  attribution_count,
            "has_any_sources":    url_count > 0 or quote_count > 0 or attribution_count > 0,
            "description":        self._build_description(
                url_count, quote_count, attribution_count, score
            ),
        }

    # ------------------------------------------------------------------
    def _build_description(
        self,
        urls: int,
        quotes: int,
        attributions: int,
        score: float,
    ) -> str:
        parts: list[str] = []

        if urls == 0 and quotes == 0 and attributions == 0:
            parts.append(
                "Artykuł nie zawiera żadnych weryfikowalnych źródeł, cytowań "
                "ani przypisań do konkretnych osób lub instytucji."
            )
        else:
            if urls:
                parts.append(
                    f"Znaleziono {urls} link{'i' if urls > 1 else ''} "
                    f"do źródeł zewnętrznych."
                )
            if quotes:
                parts.append(
                    f"Artykuł zawiera {quotes} bezpośredni"
                    f"{'e cytaty' if quotes > 1 else ' cytat'} ze źródeł."
                )
            if attributions:
                parts.append(
                    f"Wykryto {attributions} przypisań wypowiedzi "
                    f"do konkretnych osób lub instytucji."
                )

        if score >= 70:
            parts.append("Źródłowanie artykułu jest na dobrym poziomie.")
        elif score >= 40:
            parts.append("Artykuł ma częściowe oparcie w źródłach — mogłoby ich być więcej.")
        else:
            parts.append("Brakuje wystarczającego udokumentowania twierdzeń w źródłach.")

        return " ".join(parts)
