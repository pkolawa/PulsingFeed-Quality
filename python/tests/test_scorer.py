"""Testy agregatora wyników (wagi kategorii, oceny hybrydowe, opisy, metadane)."""
from datetime import datetime

import pytest

from analyzer.scorer import ArticleScorer
from config import ANALYSIS_VERSION, CATEGORY_WEIGHTS


def make_det(linguistic=70.0, structure=50.0, sources=40.0, sensationalism=100.0) -> dict:
    return {
        "linguistic":     {"score": linguistic, "description": "Opis językowy."},
        "structure":      {"score": structure, "description": "Opis struktury."},
        "sources":        {"score": sources, "description": "Opis źródeł."},
        "sensationalism": {"score": sensationalism, "description": "Opis sensacji."},
    }


def make_llm(factuality=80.0, logic=60.0, journalism=50.0) -> dict:
    return {
        "factuality_score": factuality, "factuality_description": "Opis faktów.",
        "logic_score": logic, "logic_description": "Opis logiki.",
        "journalism_score": journalism, "journalism_description": "Opis warsztatu.",
        "overall_description": "Opis ogólny.",
        "model": "fake-model",
    }


@pytest.fixture
def scorer() -> ArticleScorer:
    return ArticleScorer()


# ── Wagi i wyniki ────────────────────────────────────────────────────
def test_wagi_kategorii_sumuja_sie_do_jedynki():
    assert sum(CATEGORY_WEIGHTS.values()) == pytest.approx(1.0)


def test_wynik_jezykowy_i_dziennikarski_sa_hybrydowe(scorer):
    result = scorer.compute(1, make_det(), make_llm())
    # 70 * 0,7 + 50 * 0,2 + 100 * 0,1
    assert result["linguistic_score"] == 69.0
    # 50 * 0,7 + 100 * 0,3
    assert result["journalism_score"] == 65.0


def test_wynik_laczny_stosuje_wagi(scorer):
    result = scorer.compute(1, make_det(), make_llm())
    # 80 * 0,3 + 69 * 0,2 + 60 * 0,2 + 65 * 0,2 + 40 * 0,1
    assert result["total_score"] == 66.8


@pytest.mark.parametrize("value", [0.0, 100.0])
def test_skrajne_wyniki_daja_skrajny_wynik_laczny(scorer, value):
    det = make_det(value, value, value, value)
    llm = make_llm(value, value, value)
    assert scorer.compute(1, det, llm)["total_score"] == value


def test_wyniki_sa_zaokraglane_do_dwoch_miejsc(scorer):
    result = scorer.compute(1, make_det(linguistic=33.333), make_llm(factuality=66.666))
    for key in ("total_score", "factuality_score", "linguistic_score"):
        assert result[key] == round(result[key], 2)
    assert result["factuality_score"] == 66.67


def test_sensacjonalizm_obniza_jezykowa_i_dziennikarstwo(scorer):
    clean = scorer.compute(1, make_det(sensationalism=100.0), make_llm())
    tabloid = scorer.compute(1, make_det(sensationalism=0.0), make_llm())
    assert tabloid["linguistic_score"] == clean["linguistic_score"] - 10.0
    assert tabloid["journalism_score"] == clean["journalism_score"] - 30.0


def test_brak_wynikow_llm_daje_wartosc_domyslna(scorer):
    result = scorer.compute(1, make_det(), {})
    assert result["factuality_score"] == 50.0
    assert result["logic_score"] == 50.0
    assert result["llm_model"] == "unknown"
    assert result["factuality_description"] == ""


# ── Opisy ────────────────────────────────────────────────────────────
def test_opisy_hybrydowe_lacza_oba_zrodla(scorer):
    result = scorer.compute(1, make_det(), make_llm())
    assert result["linguistic_description"] == "Opis językowy. Opis struktury."
    assert result["journalism_description"] == "Opis warsztatu. Opis sensacji."
    assert result["sources_description"] == "Opis źródeł."


def test_puste_opisy_nie_zostawiaja_spacji(scorer):
    det = make_det()
    det["linguistic"]["description"] = ""
    det["sensationalism"]["description"] = ""
    llm = make_llm()
    llm["journalism_description"] = ""

    result = scorer.compute(1, det, llm)

    assert result["linguistic_description"] == "Opis struktury."
    assert result["journalism_description"] == ""


# ── Metadane ─────────────────────────────────────────────────────────
def test_metadane_i_dane_surowe(scorer):
    det, llm = make_det(), make_llm()
    result = scorer.compute(42, det, llm)

    assert result["article_id"] == 42
    assert result["llm_model"] == "fake-model"
    assert result["analysis_version"] == ANALYSIS_VERSION
    assert result["deterministic_data"] is det
    assert result["llm_data"] is llm
    assert datetime.fromisoformat(result["analyzed_at"]).tzinfo is not None
