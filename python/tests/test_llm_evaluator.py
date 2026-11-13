"""Testy LLMEvaluator: parsowanie odpowiedzi modelu, wynik zastępczy, przycinanie treści."""
import json

import pytest

from analyzer.llm import evaluator as evaluator_module
from analyzer.llm.evaluator import MAX_CONTENT_CHARS, LLMEvaluator


def llm_json(**overrides) -> str:
    data = {
        "factuality": {"score": 80, "description": "Fakty.", "flags": {"data_is_precise": True}},
        "logic":      {"score": 70, "description": "Logika.", "flags": {"narrative_is_clear": True}},
        "journalism": {"score": 60, "description": "Warsztat.", "flags": {"clickbait_headline": False}},
        "overall_description": "Ogólnie dobrze.",
    }
    data.update(overrides)
    return json.dumps(data)


class FakeClient:
    """Atrapa LLMClient: zwraca przygotowaną odpowiedź albo rzuca wyjątek."""
    model = "fake-model"

    def __init__(self):
        self.response = llm_json()
        self.error = None
        self.prompts: list[str] = []

    def complete(self, system, prompt, max_tokens=1_500):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.response, 123


@pytest.fixture
def client(monkeypatch) -> FakeClient:
    fake = FakeClient()
    monkeypatch.setattr(evaluator_module, "LLMClient", lambda: fake)
    return fake


@pytest.fixture
def evaluator(client) -> LLMEvaluator:
    return LLMEvaluator()


def assert_fallback(result: dict) -> None:
    assert result["success"] is False
    assert result["error"]
    assert result["factuality_score"] == 50.0
    assert result["logic_score"] == 50.0
    assert result["journalism_score"] == 50.0
    assert result["tokens_used"] == 0
    assert result["model"] == "unknown"


# ── Poprawna odpowiedź ───────────────────────────────────────────────
def test_poprawna_odpowiedz_daje_wyniki_opisy_i_flagi(evaluator):
    result = evaluator.evaluate("Tytuł", "Treść")

    assert result["success"] is True
    assert result["factuality_score"] == 80.0
    assert result["logic_score"] == 70.0
    assert result["journalism_score"] == 60.0
    assert result["factuality_description"] == "Fakty."
    assert result["overall_description"] == "Ogólnie dobrze."
    assert result["factuality_flags"] == {"data_is_precise": True}
    assert result["logic_flags"] == {"narrative_is_clear": True}
    assert result["journalism_flags"] == {"clickbait_headline": False}
    assert result["tokens_used"] == 123
    assert result["model"] == "fake-model"


@pytest.mark.parametrize("wrap", [
    "Oto ocena:\n{}\nDziękuję.",
    "```json\n{}\n```",
])
def test_json_otoczony_tekstem_jest_wycinany(evaluator, client, wrap):
    client.response = wrap.replace("{}", llm_json())
    assert evaluator.evaluate("T", "C")["success"] is True


@pytest.mark.parametrize("raw, expected", [
    (150, 100.0),
    (-5, 0.0),
    (100, 100.0),
    (0, 0.0),
    (73.5, 73.5),
    ("75", 75.0),
])
def test_wynik_jest_liczba_w_zakresie_0_100(evaluator, client, raw, expected):
    client.response = llm_json(factuality={"score": raw, "description": "", "flags": {}})
    result = evaluator.evaluate("T", "C")
    assert result["success"] is True
    assert result["factuality_score"] == expected


# ── Niepoprawna odpowiedź ────────────────────────────────────────────
@pytest.mark.parametrize("response", [
    "Nie potrafię ocenić tego artykułu.",
    "",
    '{"factuality": {"score": 80',
    "{to nie jest json}",
])
def test_odpowiedz_bez_poprawnego_jsona_daje_fallback(evaluator, client, response):
    client.response = response
    assert_fallback(evaluator.evaluate("T", "C"))


@pytest.mark.parametrize("score", ["wysoki", None, [80]])
def test_wynik_nieliczbowy_daje_fallback(evaluator, client, score):
    client.response = llm_json(logic={"score": score, "description": "", "flags": {}})
    assert_fallback(evaluator.evaluate("T", "C"))


def test_blad_klienta_nie_wychodzi_na_zewnatrz(evaluator, client):
    client.error = RuntimeError("API niedostępne")
    result = evaluator.evaluate("T", "C")
    assert_fallback(result)
    assert result["error"] == "API niedostępne"
    assert "API niedostępne" in result["overall_description"]


# Brakujący wynik nie może zamienić się w sztuczne 50 zapisane jako 'done'
@pytest.mark.parametrize("response", [
    "{}",
    llm_json(factuality={"description": "Bez wyniku.", "flags": {}}),
    json.dumps({"logic": {"score": 70}, "journalism": {"score": 60}}),
    llm_json(journalism="dobry warsztat"),
    llm_json(logic={"score": float("nan"), "description": "", "flags": {}}),
])
def test_niepelna_odpowiedz_daje_fallback(evaluator, client, response):
    client.response = response
    assert_fallback(evaluator.evaluate("T", "C"))


# ── Budowa promptu ───────────────────────────────────────────────────
def test_tresc_do_limitu_nie_jest_przycinana(evaluator, client):
    evaluator.evaluate("T", "x" * MAX_CONTENT_CHARS)
    assert "x" * MAX_CONTENT_CHARS in client.prompts[0]
    assert "tekst skrócony" not in client.prompts[0]


def test_dluga_tresc_jest_przycinana_z_adnotacja(evaluator, client):
    evaluator.evaluate("T", "x" * MAX_CONTENT_CHARS + "KONIEC")
    assert "KONIEC" not in client.prompts[0]
    assert "tekst skrócony" in client.prompts[0]


def test_pusty_tytul_ma_zastepczy_opis(evaluator, client):
    evaluator.evaluate("", "Treść")
    assert "(brak tytułu)" in client.prompts[0]


def test_klamry_w_artykule_nie_psuja_szablonu(evaluator, client):
    result = evaluator.evaluate("Tytuł {x}", "Kod: {y} i {} oraz {0}")
    assert result["success"] is True
    assert "Tytuł {x}" in client.prompts[0]
    assert "Kod: {y} i {} oraz {0}" in client.prompts[0]
