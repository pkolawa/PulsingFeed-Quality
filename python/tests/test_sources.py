"""Testy analizatora źródeł (linki, cytaty, atrybucje)."""
import pytest

from analyzer.deterministic.sources import SourcesAnalyzer

# Wypełniacz bez linków, cytatów i wyrażeń atrybucyjnych
WYPELNIACZ = " ".join(["słowo"] * 250)


@pytest.fixture
def analyzer() -> SourcesAnalyzer:
    return SourcesAnalyzer()


# ── Brak źródeł ──────────────────────────────────────────────────────
def test_long_article_without_sources(analyzer):
    result = analyzer.analyze(WYPELNIACZ)
    assert result["score"] == 5.0
    assert result["has_any_sources"] is False
    assert "nie zawiera żadnych weryfikowalnych źródeł" in result["description"]


def test_short_news_without_sources_is_treated_leniently(analyzer):
    result = analyzer.analyze("Pociąg odjechał z opóźnieniem.")
    assert result["score"] == 20.0
    assert result["has_any_sources"] is False


# ── Linki ────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("linki", "oczekiwany"), [(1, 12.0), (2, 24.0), (3, 25.0)])
def test_urls_score_with_cap(analyzer, linki, oczekiwany):
    urls = " ".join(f"https://example.com/raport-{i}" for i in range(linki))
    result = analyzer.analyze(f"Pełny raport: {urls}")
    assert result["url_count"] == linki
    assert result["score"] == oczekiwany


def test_url_detection_stops_at_quotes_and_whitespace(analyzer):
    result = analyzer.analyze('<a href="http://gov.pl/dane">dane</a> oraz https://stat.gov.pl.')
    assert result["url_count"] == 2


# ── Cytaty ───────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "cytat",
    [
        "„To jest bardzo ważna decyzja dla kraju”",
        '"To jest bardzo ważna decyzja dla kraju"',
        "«To jest bardzo ważna decyzja dla kraju»",
    ],
)
def test_quote_styles_are_detected(analyzer, cytat):
    result = analyzer.analyze(f"Usłyszeliśmy: {cytat}.")
    assert result["quote_count"] == 1
    assert result["score"] == 12.0


def test_too_short_quote_is_ignored(analyzer):
    assert analyzer.analyze("Odpowiedź brzmiała „Tak”.")["quote_count"] == 0


def test_quotes_score_is_capped(analyzer):
    cytaty = " ".join(f"„Wypowiedź numer {i} jest dość długa”" for i in range(4))
    result = analyzer.analyze(cytaty)
    assert result["quote_count"] == 4
    assert result["score"] == 35.0


# ── Atrybucje ────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "fraza",
    [
        "Według ministra sytuacja jest stabilna.",
        "WEDŁUG ekspertów sytuacja jest stabilna.",
        "Zdaniem analityków sytuacja jest stabilna.",
        "Jak podaje GUS, sytuacja jest stabilna.",
        "W ocenie banku sytuacja jest stabilna.",
        "Informację podał dr Kowalski.",
        "Sytuacja jest stabilna, za PAP.",
        "Rząd poinformował o zmianach.",
    ],
)
def test_attribution_phrases_are_detected(analyzer, fraza):
    result = analyzer.analyze(fraza)
    assert result["attribution_count"] == 1
    assert result["has_any_sources"] is True


def test_nearby_attributions_are_grouped(analyzer):
    # "Rzecznik" i "powiedział" leżą w tym samym 50-znakowym oknie
    result = analyzer.analyze("Rzecznik powiedział, że sytuacja jest stabilna.")
    assert result["attribution_count"] == 1


def test_attributions_score_is_capped(analyzer):
    zdania = [f"Według ministra {i} sytuacja jest stabilna i spokojna." for i in range(6)]
    result = analyzer.analyze(" ".join(zdania))
    assert result["attribution_count"] == 6
    assert result["score"] == 40.0


# ── Wynik łączny ─────────────────────────────────────────────────────
def test_well_sourced_article_reaches_full_score(analyzer):
    linki = " ".join(f"https://example.com/raport-{i}" for i in range(3))
    cytaty = " ".join(f"„Wypowiedź numer {i} jest dość długa”" for i in range(3))
    atrybucje = " ".join(
        f"Według ministra {i} sytuacja jest stabilna i spokojna." for i in range(5)
    )
    result = analyzer.analyze(f"{linki} {cytaty} {atrybucje}")
    assert result["score"] == 100.0
    assert "na dobrym poziomie" in result["description"]


def test_description_lists_found_source_types(analyzer):
    result = analyzer.analyze(
        "Według ministra „to jest bardzo ważna decyzja”. Raport: https://gov.pl/r"
    )
    desc = result["description"]
    assert "1 link do źródeł" in desc
    assert "1 bezpośredni cytat" in desc
    assert "przypisań wypowiedzi" in desc
