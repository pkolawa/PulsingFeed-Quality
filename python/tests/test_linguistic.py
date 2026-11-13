"""Testy analizatora poprawności językowej (regex + statystyki)."""
import pytest

from analyzer.deterministic.linguistic import LinguisticAnalyzer

# Poprawne zdanie z 20 słów — mieści się w optymalnej długości (15–25)
ZDANIE = (
    "Rada Ministrów przyjęła we wtorek projekt ustawy budżetowej na przyszły rok, "
    "który zakłada wyraźny wzrost wydatków na ochronę zdrowia obywateli."
)


def tekst(zdan: int) -> str:
    return " ".join([ZDANIE] * zdan)


@pytest.fixture
def analyzer() -> LinguisticAnalyzer:
    return LinguisticAnalyzer()


# ── Przypadki brzegowe ───────────────────────────────────────────────
@pytest.mark.parametrize("content", ["", "   \n\t  "])
def test_empty_content(analyzer, content):
    result = analyzer.analyze(content)
    assert result["score"] == 0.0
    assert result["word_count"] == 0
    assert result["description"] == "Brak treści do analizy."


def test_clean_text_gets_full_score(analyzer):
    result = analyzer.analyze(tekst(3))
    assert result["total_errors"] == 0
    assert result["word_count"] == 60
    assert result["sentence_count"] == 3
    assert result["avg_sentence_length"] == 20.0
    assert result["score"] == 100.0
    assert "poprawnie językowo" in result["description"]


def test_title_is_included_in_analysis(analyzer):
    result = analyzer.analyze(tekst(1), title="Budżet  przyjęty")
    assert result["word_count"] == 22
    assert result["punctuation_errors"] == 1   # podwójna spacja w tytule


# ── Wykrywanie błędów ────────────────────────────────────────────────
@pytest.mark.parametrize(
    "fragment",
    [
        "Ala  ma kota.",            # podwójna spacja
        "Ala ma kota .",            # spacja przed kropką
        "Czy Ala ma kota?!?",       # powtórzona interpunkcja
        "Ala ma kota.. Potem nie.", # dwie kropki zamiast wielokropka
    ],
)
def test_punctuation_errors(analyzer, fragment):
    result = analyzer.analyze(fragment)
    assert result["punctuation_errors"] == 1
    assert result["spelling_errors"] == 0


def test_lowercase_after_sentence_end(analyzer):
    result = analyzer.analyze("To jest koniec. potem jest dalej.")
    assert result["spelling_errors"] == 1
    assert result["punctuation_errors"] == 0


# ── Punktacja ────────────────────────────────────────────────────────
def test_score_formula(analyzer):
    # 100 słów, 1 błąd → 10/1000 → 100 - 60 = 40, +5 za długość zdań
    content = tekst(5).replace("Rada Ministrów", "Rada  Ministrów", 1)
    result = analyzer.analyze(content)
    assert result["errors_per_1000_words"] == 10.0
    assert result["score"] == 45.0


def test_base_score_has_floor(analyzer):
    result = analyzer.analyze("jeden  dwa  trzy  cztery  pięć  sześć  siedem  osiem  dziewięć  dziesięć")
    assert result["total_errors"] == 9
    assert result["score"] == 10.0


def test_short_sentences_are_penalized(analyzer):
    result = analyzer.analyze("Rząd zebrał się. Ministrowie dyskutowali długo. Decyzji nie podjęto.")
    assert result["avg_sentence_length"] == 3.0
    assert result["score"] == 95.0
    assert "bardzo krótkie" in result["description"]


def test_long_sentences_are_penalized(analyzer):
    result = analyzer.analyze(" ".join(["słowo"] * 45) + ".")
    assert result["avg_sentence_length"] == 45.0
    assert result["score"] == 90.0
    assert "bardzo długie" in result["description"]


def test_description_mentions_error_types(analyzer):
    result = analyzer.analyze("Ala  ma kota. potem psa.")
    assert "1 ortograficznych" in result["description"]
    assert "1 interpunkcyjnych" in result["description"]


# ── Regresje heurystyk ───────────────────────────────────────────────
def test_proper_ellipsis_is_not_an_error(analyzer):
    assert analyzer.analyze("Czekał... Potem wrócił.")["punctuation_errors"] == 0


def test_decimal_numbers_and_times_are_not_errors(analyzer):
    assert analyzer.analyze("Wzrost wyniósł 3,5 proc. O godzinie 12:30 ogłoszono wynik.")["punctuation_errors"] == 0


@pytest.mark.parametrize("fragment", ["Przyszli Ala,Ola i Ela.", "Plan:wyjazd o 5.", "Wynik 5,a nie 6."])
def test_missing_space_after_punctuation_is_counted_once(analyzer, fragment):
    assert analyzer.analyze(fragment)["punctuation_errors"] == 1


def test_lowercase_polish_letter_after_sentence_end(analyzer):
    assert analyzer.analyze("To jest koniec. żaden problem.")["spelling_errors"] == 1
