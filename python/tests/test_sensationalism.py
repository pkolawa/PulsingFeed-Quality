"""Testy analizatora sensacjonalizmu i clickbaitu."""
import pytest

from analyzer.deterministic.sensationalism import SensationalismAnalyzer

RZETELNY_TYTUL = "Rząd przyjął projekt budżetu"
RZETELNA_TRESC = (
    "Rada Ministrów przyjęła we wtorek projekt ustawy budżetowej na przyszły rok. "
    "Dokument trafi teraz do Sejmu, gdzie rozpoczną się prace w komisjach."
)


@pytest.fixture
def analyzer() -> SensationalismAnalyzer:
    return SensationalismAnalyzer()


def test_neutral_article_gets_full_score(analyzer):
    result = analyzer.analyze(RZETELNA_TRESC, title=RZETELNY_TYTUL)
    assert result["score"] == 100.0
    assert result["penalty"] == 0.0
    assert result["sensational_word_count"] == 0
    assert result["clickbait_patterns"] == 0
    assert "nie wykazuje cech sensacjonalizmu" in result["description"]


def test_tabloid_article_gets_low_score(analyzer):
    result = analyzer.analyze(
        "SZOK! To prawdziwy SKANDAL! Nie uwierzysz, co się stało! Afera i dramat!",
        title="SZOK!!! SKANDAL W SEJMIE!",
    )
    assert result["score"] < 30
    assert "znacząco odbiega" in result["description"]


# ── Słownictwo sensacyjne ────────────────────────────────────────────
def test_sensational_words_are_detected_case_insensitively(analyzer):
    result = analyzer.analyze(f"{RZETELNA_TRESC} Wybuchł Skandal, a potem afera.")
    assert result["sensational_word_count"] == 2
    assert set(result["sensational_words"]) == {"skandal", "afera"}


def test_multiword_sensational_phrases(analyzer):
    result = analyzer.analyze(f"{RZETELNA_TRESC} Nie uwierzysz, ale internet szaleje.")
    assert set(result["sensational_words"]) == {"nie uwierzysz", "internet szaleje"}


def test_sensational_terms_respect_word_boundaries(analyzer):
    # "dramaturg" nie powinien być liczony jako "dramat"
    result = analyzer.analyze("Znany dramaturg wystawił nową sztukę w teatrze.")
    assert result["sensational_word_count"] == 0


def test_sensational_words_list_is_truncated(analyzer):
    terms = "szok sensacja skandal rewelacja pilne katastrofa apokalipsa dramat tragedia afera masakra patologia"
    result = analyzer.analyze(terms)
    assert len(result["sensational_words"]) == 10


# ── Clickbait ────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "tytul",
    [
        "10 powodów, dla których warto oszczędzać",
        "Oto dlaczego ceny rosną",
        "Co musisz wiedzieć o nowych podatkach",
        "Prawda o emeryturach",
        "Sekretny składnik diety",
        "Cały internet o tym mówi",
    ],
)
def test_clickbait_patterns_in_title(analyzer, tytul):
    result = analyzer.analyze(RZETELNA_TRESC, title=tytul)
    assert result["clickbait_patterns"] >= 1
    assert result["score"] < 100


def test_clickbait_is_checked_only_at_beginning(analyzer):
    content = " ".join(["słowo"] * 100) + " Oto dlaczego ceny rosną."
    assert len(content.split("Oto")[0]) > 400
    assert analyzer.analyze(content)["clickbait_patterns"] == 0


# ── CAPS i wykrzykniki ───────────────────────────────────────────────
def test_caps_ratio(analyzer):
    # 2 z 10 słów zapisane wielkimi literami (krótkie słowa ≤ 2 znaki pomijane)
    result = analyzer.analyze("UWAGA to jest WAŻNE ale nie ma w tym OK")
    assert result["caps_ratio"] == 0.2


def test_exclamations_are_penalized(analyzer):
    spokojny = analyzer.analyze(RZETELNA_TRESC)
    krzykliwy = analyzer.analyze(RZETELNA_TRESC.replace(".", "!"))
    assert krzykliwy["exclamation_count"] == 2
    assert krzykliwy["score"] < spokojny["score"]


# ── Nagłówek ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("tytul", "oczekiwany"),
    [
        (RZETELNY_TYTUL, 100.0),
        ("Rząd przyjął projekt budżetu!", 85.0),
        ("Rząd przyjął projekt budżetu!!!", 70.0),   # kara za ! ograniczona do 30
        ("Czy rząd przyjmie budżet??", 85.0),
        ("Skandal w rządzie", 85.0),
        ("SZOK! SKANDAL!", 0.0),
    ],
)
def test_title_score(analyzer, tytul, oczekiwany):
    assert analyzer._score_title(tytul) == oczekiwany


def test_sensational_title_lowers_score(analyzer):
    neutral = analyzer.analyze(RZETELNA_TRESC, title=RZETELNY_TYTUL)
    sensational = analyzer.analyze(RZETELNA_TRESC, title="SKANDAL W RZĄDZIE!")
    assert sensational["score"] < neutral["score"]


def test_score_is_never_negative(analyzer):
    result = analyzer.analyze("SZOK!!! " * 50, title="SZOK!!! SKANDAL!!!")
    assert result["penalty"] == 100.0
    assert result["score"] == 0.0
