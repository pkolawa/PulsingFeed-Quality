"""
Analiza deterministyczna — sensacjonalizm i clickbait.

Wykrywa cechy tabloidyzacji: duże litery, wykrzykniki, nacechowane emocjonalnie
słownictwo, schematy clickbaitowe. Wynik (0–100) oznacza stopień BRAKU
sensacjonalizmu (100 = tekst całkowicie pozbawiony sensacjonalizmu).
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Słownik polskich wyrażeń sensacyjnych / tabloidowych
# ---------------------------------------------------------------------------
SENSATIONAL_TERMS: list[str] = [
    # Wykrzykniki emocjonalne
    "szok", "szokujące", "szokujący", "szokuje", "szokował",
    "sensacja", "sensacyjny", "sensacyjne",
    "skandal", "skandaliczny", "skandaliczne",
    "rewelacja", "rewelacyjny", "rewelacje",
    "ekskluzywnie", "ekskluzywny", "ekskluzywne",
    # Pilność
    "pilne", "pilna", "pilny", "breaking",
    "tylko u nas", "wyłącznie u nas",
    # Katastrofizm
    "katastrofa", "apokalipsa", "koniec świata",
    "dramat", "dramatyczny", "dramatyczne",
    "tragedia", "tragiczny", "tragiczne",
    "afera", "kompromitacja", "masakra",
    # Manipulacja emocjami
    "oburzający", "oburzające", "haniebny", "haniebne",
    "patologia", "patologiczny", "niemoralne",
    "wstydliwy", "wstydliwe",
    # Clickbait superlativa
    "nigdy wcześniej", "po raz pierwszy w historii",
    "bezprecedensowy", "bezprecedensowe",
    "niewyobrażalny", "nie do wiary", "nie do pomyślenia",
    # Clickbait wezwania do akcji
    "nie uwierzysz", "musisz to zobaczyć",
    "musisz wiedzieć", "internet szaleje",
    "zszokuje cię", "to cię zszokuje",
    "podbił internet", "podbija internet",
    "pokochają cię", "wszyscy mówią",
    "to zmieni wszystko",
]

# Schematyczne wzorce clickbaitowe
CLICKBAIT_PATTERNS: list[str] = [
    r"\d+\s+(?:powodów|rzeczy|faktów|sposobów|zasad|trików|kroków|porad)",
    r"\boto\s+(?:dlaczego|co|jak|kiedy|gdzie)\b",
    r"\bco\s+(?:musisz|powinieneś|powinnaś|warto)\s+wiedzieć\b",
    r"\bprawda\s+o\s+\w+",
    r"\bsekret\w*\s+\w+",
    r"\btak\s+naprawdę\b",
    r"\bszokująca\s+prawda\b",
    r"\bto,\s+czego\s+nie\s+wiedzieli?ś?\b",
    r"\bcały\s+internet\b",
    r"[!]{2,}",                          # dwa lub więcej wykrzykników z rzędu
]

SENSATIONAL_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in SENSATIONAL_TERMS) + r")\b",
    re.IGNORECASE,
)
CLICKBAIT_COMPILED = [re.compile(p, re.IGNORECASE) for p in CLICKBAIT_PATTERNS]


class SensationalismAnalyzer:
    """
    Wykrywa cechy sensacjonalizmu i clickbaitu.

    Zwraca wynik odzwierciedlający jakość (0 = skrajnie sensacyjny, 100 = rzetelny).
    """

    def analyze(self, content: str, title: str = "") -> dict[str, Any]:
        full_text = f"{title}\n{content}" if title else content
        words     = full_text.split()
        word_count = max(len(words), 1)

        # --- Wskaźnik wielkich liter (ALL-CAPS słowa > 2 znaki) ---
        all_caps_words = sum(1 for w in words if len(w) > 2 and w.isupper())
        caps_ratio = all_caps_words / word_count

        # --- Częstość wykrzykników ---
        exclamation_count = full_text.count("!")
        exclamation_per_100 = exclamation_count / (word_count / 100)

        # --- Sensacyjne słownictwo ---
        sensational_found = SENSATIONAL_RE.findall(full_text)
        sensational_count = len(sensational_found)
        sensational_density = sensational_count / (word_count / 100)

        # --- Wzorce clickbaitowe (sprawdzane głównie na tytule i początku) ---
        check_zone = (title + " " + content[:400]) if title else content[:400]
        clickbait_hits = sum(
            1 for p in CLICKBAIT_COMPILED if p.search(check_zone)
        )

        # --- Osobna kara za tytuł ---
        title_penalty = (100.0 - self._score_title(title)) * 0.30 if title else 0.0

        # --- Łączna kara sensacjonalizmu (0–100) ---
        penalty = 0.0
        penalty += min(35.0, caps_ratio * 300.0)          # do 35 pkt za CAPS
        penalty += min(20.0, exclamation_per_100 * 8.0)   # do 20 pkt za wykrzykniki
        penalty += min(25.0, sensational_density * 12.0)  # do 25 pkt za słownictwo
        penalty += min(20.0, clickbait_hits * 7.0)        # do 20 pkt za clickbait
        penalty += title_penalty
        penalty = min(100.0, penalty)

        quality_score = max(0.0, 100.0 - penalty)

        return {
            "score":                  round(quality_score, 2),
            "penalty":                round(penalty, 2),
            "caps_ratio":             round(caps_ratio, 4),
            "exclamation_count":      exclamation_count,
            "sensational_word_count": sensational_count,
            "sensational_words":      list(set(w.lower() for w in sensational_found))[:10],
            "clickbait_patterns":     clickbait_hits,
            "description":            self._build_description(
                caps_ratio, exclamation_count, sensational_count,
                clickbait_hits, penalty
            ),
        }

    # ------------------------------------------------------------------
    def _score_title(self, title: str) -> float:
        """Ocena (0–100) samego nagłówka pod kątem sensacjonalizmu."""
        score = 100.0
        if title.isupper():
            score -= 40.0
        score -= min(30.0, title.count("!") * 15.0)
        if title.count("?") > 1:
            score -= 15.0
        sensational = SENSATIONAL_RE.findall(title)
        score -= min(30.0, len(sensational) * 15.0)
        return max(0.0, score)

    # ------------------------------------------------------------------
    def _build_description(
        self,
        caps_ratio: float,
        exclamations: int,
        sensational: int,
        clickbait: int,
        penalty: float,
    ) -> str:
        issues: list[str] = []
        if caps_ratio > 0.04:
            issues.append(f"nadmierne użycie wielkich liter ({caps_ratio:.1%} słów)")
        if exclamations > 3:
            issues.append(f"wykrzykniki ({exclamations})")
        if sensational > 0:
            issues.append(f"sensacyjne słownictwo ({sensational} wyrażeń)")
        if clickbait > 0:
            issues.append(f"schematy clickbaitowe ({clickbait})")

        parts: list[str] = []
        if not issues:
            parts.append("Artykuł nie wykazuje cech sensacjonalizmu ani clickbaitu.")
        else:
            parts.append(f"Wykryto cechy tabloidyzacji: {', '.join(issues)}.")

        if penalty > 60:
            parts.append("Styl znacząco odbiega od standardów rzetelnego dziennikarstwa.")
        elif penalty > 30:
            parts.append("Artykuł wykazuje umiarkowane cechy sensacjonalistyczne.")
        elif issues:
            parts.append("Incydentalne cechy sensacyjne nie dominują w tekście.")

        return " ".join(parts)
