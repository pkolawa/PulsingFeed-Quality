"""Testy analizatora struktury artykułu (długość, akapity, nagłówek)."""
import pytest

from analyzer.deterministic.structure import StructureAnalyzer


def tekst(slow: int, akapity: int = 1) -> str:
    """Generuje tekst o zadanej liczbie słów podzielony na akapity."""
    words = ["słowo"] * slow
    size = -(-slow // akapity)  # zaokrąglenie w górę
    chunks = [" ".join(words[i:i + size]) for i in range(0, slow, size)]
    return "\n\n".join(chunks)


@pytest.fixture
def analyzer() -> StructureAnalyzer:
    return StructureAnalyzer()


# ── Długość artykułu ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("slow", "oczekiwany"),
    [
        (50, 15.0),       # bardzo krótki
        (100, 40.0),      # próg MIN_WORDS_SHORT
        (200, 55.0),      # interpolacja 40 → 70
        (300, 70.0),      # próg MIN_WORDS_ADEQUATE
        (400, 85.0),      # interpolacja 70 → 100
        (500, 100.0),     # próg MIN_WORDS_GOOD
        (2_500, 100.0),   # górna granica optimum
        (3_500, 97.0),    # łagodna kara za długość
        (10_000, 85.0),   # kara nie spada poniżej 85
    ],
)
def test_length_score(analyzer, slow, oczekiwany):
    result = analyzer.analyze(tekst(slow))
    assert result["word_count"] == slow
    assert result["length_score"] == pytest.approx(oczekiwany)


# ── Podział na akapity ───────────────────────────────────────────────
@pytest.mark.parametrize(
    ("akapity", "oczekiwany"),
    [(1, 45.0), (2, 65.0), (3, 80.0), (4, 80.0), (5, 100.0), (8, 100.0)],
)
def test_structure_score_by_paragraphs(analyzer, akapity, oczekiwany):
    result = analyzer.analyze(tekst(400, akapity))
    assert result["paragraph_count"] == akapity
    assert result["structure_score"] == oczekiwany


def test_single_newlines_used_as_fallback_paragraphs(analyzer):
    result = analyzer.analyze("pierwszy akapit\ndrugi akapit\ntrzeci akapit")
    assert result["paragraph_count"] == 3


def test_avg_paragraph_length(analyzer):
    result = analyzer.analyze(tekst(400, 4))
    assert result["avg_para_length"] == 100.0


# ── Nagłówek ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("tytul", "oczekiwany"),
    [
        ("Rząd przyjął projekt budżetu na przyszły rok", 100.0),
        ("Budżet", 80.0),                                   # < 3 słów
        (" ".join(["słowo"] * 17), 90.0),                   # > 16 słów
        ("Rząd przyjął projekt budżetu!", 88.0),             # jeden wykrzyknik
        ("Rząd przyjął projekt budżetu!!", 70.0),            # dwa wykrzykniki
        ("Czy rząd przyjmie budżet??", 85.0),                # wiele pytajników
        ("Rząd PRZYJĄŁ projekt BUDŻETU", 80.0),              # CAPS w środku
        ("RZĄD PRZYJĄŁ BUDŻET", 45.0),                       # cały CAPS + CAPS w środku
    ],
)
def test_headline_score(analyzer, tytul, oczekiwany):
    result = analyzer.analyze(tekst(400), title=tytul)
    assert result["headline_score"] == oczekiwany


def test_missing_title_gets_neutral_headline_score(analyzer):
    assert analyzer.analyze(tekst(400))["headline_score"] == 70.0


def test_headline_score_never_negative(analyzer):
    result = analyzer.analyze(tekst(400), title="SZOK!! CO ZROBIŁ MINISTER??")
    assert result["headline_score"] == 0.0


# ── Wynik łączny ─────────────────────────────────────────────────────
def test_combined_score_weights(analyzer):
    # 400 słów (85) * 0.5 + 2 akapity (65) * 0.3 + brak tytułu (70) * 0.2
    result = analyzer.analyze(tekst(400, 2))
    assert result["score"] == pytest.approx(42.5 + 19.5 + 14.0)


def test_well_structured_article_gets_full_score(analyzer):
    result = analyzer.analyze(
        tekst(800, 6), title="Rząd przyjął projekt budżetu na przyszły rok"
    )
    assert result["score"] == 100.0
    assert "odpowiednią długość" in result["description"]
    assert "dobrą strukturę" in result["description"]
    assert "poprawnie i rzetelnie" in result["description"]


def test_empty_content(analyzer):
    result = analyzer.analyze("")
    assert result["word_count"] == 0
    assert result["paragraph_count"] == 1
    assert result["score"] == pytest.approx(15 * 0.5 + 45 * 0.3 + 70 * 0.2)


def test_description_flags_short_unstructured_text(analyzer):
    result = analyzer.analyze(tekst(50), title="SZOK!!")
    assert "bardzo krótki" in result["description"]
    assert "niepodzielony blok" in result["description"]
    assert "sensacjonalizmu" in result["description"]
