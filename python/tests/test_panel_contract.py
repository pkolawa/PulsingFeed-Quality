"""Kontrakt pipeline ↔ baza ↔ panel: pola zapisywane przez workera muszą zgadzać się z tym, co czyta widok artykułu."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from analyzer import pipeline as pipeline_module
from analyzer.llm import evaluator as evaluator_module
from analyzer.llm.prompts import ARTICLE_EVALUATION_SYSTEM

ROOT = Path(__file__).resolve().parents[2]
NODE_DIR = ROOT / "node"
ARTICLE_VIEW = NODE_DIR / "web" / "src" / "views" / "article.ejs"
LLM_FLAGS_MODULE = NODE_DIR / "web" / "src" / "llm-flags.js"
REPOSITORY = ROOT / "python" / "db" / "repository.py"

LLM_RESPONSE = json.dumps({
    "factuality": {
        "score": 81, "description": "Opis faktyczności.",
        "flags": {"contains_unverified_claims": False, "mixes_facts_with_opinions": False, "data_is_precise": True},
    },
    "logic": {
        "score": 72, "description": "Opis logiki.",
        "flags": {"has_internal_contradictions": False, "narrative_is_clear": True, "conclusions_follow_from_facts": True},
    },
    "journalism": {
        "score": 63, "description": "Opis warsztatu.",
        "flags": {
            "is_opinion_piece": False, "has_multiple_perspectives": True, "headline_matches_content": True,
            "maintains_neutral_tone": True, "clickbait_headline": False,
        },
    },
    "overall_description": "Opis ogólny artykułu.",
})

ARTICLE = {
    "id": 7,
    "title": "SZOK! Sejm przyjął ustawę",
    "content": "\n\n".join([
        "Sejm przyjął ustawę, co jest szokujące. Jak powiedział rzecznik, \"to ważny krok\". "
        "Więcej na https://example.org/dokument."
    ] * 6),
    "publisher_id": 1,
}


class FakeClient:
    model = "fake-model"

    def complete(self, system, prompt, max_tokens=1_500):
        return LLM_RESPONSE, 100


@pytest.fixture
def result(monkeypatch) -> dict:
    """Wynik prawdziwego pipeline'u (tylko odpowiedź modelu jest atrapą)."""
    monkeypatch.setattr(evaluator_module, "LLMClient", FakeClient)
    return pipeline_module.ArticleAnalysisPipeline().analyze(ARTICLE)


def stored(result: dict) -> dict:
    """Artykuł w kształcie odpowiedzi API: JSON-owe kolumny przechodzą przez json.dumps."""
    return json.loads(json.dumps({
        **result,
        "id": ARTICLE["id"],
        "title": ARTICLE["title"],
        "url": "https://example.org/a/7",
        "published_at": "2026-10-30T08:00:00Z",
        "collected_at": "2026-10-30T09:00:00Z",
        "analysis_status": "done",
        "publisher_id": 1,
        "publisher_name": "Wydawca testowy",
    }))


# ── Statycznie: działa bez Node ──────────────────────────────────────
def test_widok_czyta_tylko_istniejace_pola_llm(result):
    fields = set(re.findall(r"llm_data\?\.(\w+)", ARTICLE_VIEW.read_text()))
    assert fields, "Widok przestał czytać llm_data, zaktualizuj test"
    assert fields <= set(result["llm_data"])


def test_widok_czyta_tylko_istniejace_pola_deterministyczne(result):
    paths = re.findall(r"det\.(\w+)\?\.(\w+)", ARTICLE_VIEW.read_text())
    assert paths, "Widok przestał czytać dane deterministyczne, zaktualizuj test"
    det = result["deterministic_data"]
    missing = [f"{group}.{field}" for group, field in paths if field not in det.get(group, {})]
    assert missing == []


def test_repozytorium_zapisuje_pola_zwracane_przez_scorer(result):
    fields = set(re.findall(r"score\[\"(\w+)\"\]", REPOSITORY.read_text()))
    assert fields, "Repozytorium przestało czytać pola wyniku, zaktualizuj test"
    assert fields <= set(result)


# ── Pipeline ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("title, content", [(None, None), ("", ""), ("   ", "  \n ")])
def test_pipeline_znosi_pusty_artykul(monkeypatch, title, content):
    monkeypatch.setattr(evaluator_module, "LLMClient", FakeClient)
    pipeline = pipeline_module.ArticleAnalysisPipeline()
    final = pipeline.analyze({"id": 1, "title": title, "content": content})
    assert 0 <= final["total_score"] <= 100


# ── Prawdziwe renderowanie szablonu ──────────────────────────────────
RENDER_SCRIPT = """
const ejs = require('ejs');
const article = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const helpers = {
  scoreGrade: () => 'a',
  fmtDate: (iso) => String(iso),
  statusBadge: (status) => ({ cls: '', label: status }),
  flagBadge: require(process.argv[2]).flagBadge,
};
ejs.renderFile(process.argv[1], { article, ...helpers }, (err, html) => {
  if (err) { console.error(err); process.exit(1); }
  process.stdout.write(html);
});
"""


def render_article(article: dict) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("Brak Node.js")
    has_ejs = subprocess.run(
        [node, "-e", "require.resolve('ejs')"], cwd=NODE_DIR, capture_output=True
    ).returncode == 0
    if not has_ejs:
        pytest.skip("Brak zależności panelu: uruchom npm install w Quality/node")

    done = subprocess.run(
        [node, "-e", RENDER_SCRIPT, str(ARTICLE_VIEW), str(LLM_FLAGS_MODULE)],
        cwd=NODE_DIR, input=json.dumps(article), capture_output=True, text=True, timeout=30,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_widok_pokazuje_flagi_llm(result):
    html = render_article(stored(result))
    for flag in (
        "Niezweryfikowane twierdzenia: nie", "Precyzyjne dane: tak",
        "Wewnętrzne sprzeczności: nie", "Jasna narracja: tak",
        "Wiele perspektyw: tak", "Clickbaitowy nagłówek: nie",
    ):
        assert flag in html


def test_kazda_flaga_z_promptu_ma_polska_etykiete(result):
    flags = re.findall(r'"(\w+)":\s*<true\|false>', ARTICLE_EVALUATION_SYSTEM)
    assert flags, "Prompt zmienił format flag, zaktualizuj test"

    article = stored(result)
    article["llm_data"]["factuality_flags"] = {flag: True for flag in flags}
    html = render_article(article)

    assert [flag for flag in flags if flag.replace("_", " ") in html] == []


@pytest.mark.parametrize("flag, value, badge_class, text", [
    ("data_is_precise", True, "pf-badge--success", "Precyzyjne dane: tak"),
    ("data_is_precise", False, "pf-badge--error", "Precyzyjne dane: nie"),
    # Przy złych flagach „tak” jest ostrzeżeniem, a „nie” dobrą wiadomością
    ("clickbait_headline", True, "pf-badge--error", "Clickbaitowy nagłówek: tak"),
    ("clickbait_headline", False, "pf-badge--success", "Clickbaitowy nagłówek: nie"),
    ("contains_unverified_claims", True, "pf-badge--error", "Niezweryfikowane twierdzenia: tak"),
    ("has_internal_contradictions", False, "pf-badge--success", "Wewnętrzne sprzeczności: nie"),
    # Bez oceny: tekst opinii nie jest wadą, a nieznanej flagi nie umiemy ocenić
    ("is_opinion_piece", True, "", "Tekst opinii: tak"),
    ("is_opinion_piece", False, "", "Tekst opinii: nie"),
    ("nowa_flaga", True, "", "nowa flaga: tak"),
])
def test_kolor_flagi_mowi_czy_odpowiedz_jest_dobra(result, flag, value, badge_class, text):
    article = stored(result)
    article["llm_data"] = {"factuality_flags": {flag: value}}
    html = render_article(article)
    assert f'<span class="pf-badge {badge_class}">{text}</span>' in html


def test_widok_pokazuje_opisy_i_dane_deterministyczne(result):
    html = render_article(stored(result))
    for text in (
        "Opis faktyczności.", "Opis logiki.", "Opis warsztatu.", "Opis ogólny artykułu.",
        "fake-model", "szokujące",
    ):
        assert text in html

    det = result["deterministic_data"]
    cells = re.findall(r"<strong>([^<]*)</strong>", html)
    for value in (det["structure"]["word_count"], det["sources"]["url_count"], det["sources"]["quote_count"]):
        assert str(value) in cells


def test_widok_artykulu_bez_analizy_renderuje_sie():
    html = render_article({
        "id": 7, "title": "Czeka na analizę", "url": None,
        "published_at": None, "collected_at": "2026-10-30T09:00:00Z",
        "analysis_status": "pending", "publisher_id": 1, "publisher_name": "Wydawca testowy",
        "total_score": None, "factuality_score": None, "linguistic_score": None,
        "logic_score": None, "journalism_score": None, "sources_score": None,
        "overall_description": None, "factuality_description": None, "linguistic_description": None,
        "logic_description": None, "journalism_description": None, "sources_description": None,
        "deterministic_data": None, "llm_data": None,
        "llm_model": None, "analysis_version": None, "analyzed_at": None,
    })
    assert "Czeka na analizę" in html
    assert "flag-row" not in html
