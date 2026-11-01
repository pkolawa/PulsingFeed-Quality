"""Testy klienta LLM i promptu: prompt caching (stała część systemowa) i liczenie tokenów."""
import json
from types import SimpleNamespace

import pytest

from analyzer.llm import client as client_module
from analyzer.llm.evaluator import LLMEvaluator
from analyzer.llm.prompts import ARTICLE_EVALUATION_SYSTEM, ARTICLE_EVALUATION_USER


VALID_JSON = json.dumps({
    "factuality": {"score": 80, "description": "ok", "flags": {}},
    "logic":      {"score": 70, "description": "ok", "flags": {}},
    "journalism": {"score": 60, "description": "ok", "flags": {}},
    "overall_description": "ok",
})


def make_message(usage: dict, text: str = VALID_JSON, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(**usage),
    )


class FakeMessages:
    def __init__(self, message):
        self.message = message
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.message


@pytest.fixture
def fake_anthropic(monkeypatch):
    """Podmienia anthropic.Anthropic na atrapę zapisującą parametry wywołań."""
    anthropic = pytest.importorskip("anthropic")
    messages = FakeMessages(make_message({
        "input_tokens": 1200,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 900,
        "output_tokens": 300,
    }))
    monkeypatch.setattr(client_module, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(
        anthropic, "Anthropic", lambda **_: SimpleNamespace(messages=messages)
    )
    return messages


# ── Prompt ───────────────────────────────────────────────────────────
def test_czesc_systemowa_nie_zawiera_danych_artykulu():
    assert "{title}" not in ARTICLE_EVALUATION_SYSTEM
    assert "{content}" not in ARTICLE_EVALUATION_SYSTEM
    assert "ARTYKUŁ DO OCENY" not in ARTICLE_EVALUATION_SYSTEM
    # Część systemowa nie jest formatowana — przykład JSON ma pojedyncze klamry
    assert '"factuality": {' in ARTICLE_EVALUATION_SYSTEM
    assert "{{" not in ARTICLE_EVALUATION_SYSTEM


def test_szablon_uzytkownika_wstawia_tytul_i_tresc():
    rendered = ARTICLE_EVALUATION_USER.format(title="Tytuł X", content="Treść Y")
    assert "Tytuł: Tytuł X" in rendered
    assert "Treść Y" in rendered


# ── Anthropic: cache_control ─────────────────────────────────────────
def test_anthropic_wysyla_system_z_cache_control(fake_anthropic):
    provider = client_module._AnthropicProvider("claude-sonnet-5-5")
    provider.complete("STAŁA INSTRUKCJA", "artykuł", max_tokens=100)

    call = fake_anthropic.calls[0]
    assert call["system"] == [{
        "type": "text",
        "text": "STAŁA INSTRUKCJA",
        "cache_control": {"type": "ephemeral"},
    }]
    assert call["messages"] == [{"role": "user", "content": "artykuł"}]


def test_anthropic_tokeny_obejmuja_cache(fake_anthropic):
    provider = client_module._AnthropicProvider("claude-sonnet-5-5")
    _, tokens = provider.complete("s", "p", max_tokens=100)
    assert tokens == 1200 + 0 + 900 + 300


def test_anthropic_tokeny_bez_pol_cache(fake_anthropic):
    fake_anthropic.message = make_message({
        "input_tokens": 10,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": None,
        "output_tokens": 5,
    })
    provider = client_module._AnthropicProvider("claude-sonnet-5-5")
    _, tokens = provider.complete("s", "p", max_tokens=100)
    assert tokens == 15


# ── Evaluator: stały prefiks między artykułami ───────────────────────
def test_evaluator_wysyla_identyczny_system_dla_roznych_artykulow(fake_anthropic, monkeypatch):
    monkeypatch.setattr(client_module, "LLM_PROVIDER", "anthropic")
    evaluator = LLMEvaluator()

    first = evaluator.evaluate("Pierwszy", "Treść pierwszego artykułu.")
    second = evaluator.evaluate("Drugi", "Zupełnie inna treść.")

    assert first["success"] and second["success"]
    systems = [call["system"] for call in fake_anthropic.calls]
    assert systems[0] == systems[1]
    assert systems[0][0]["text"] == ARTICLE_EVALUATION_SYSTEM
    assert "Pierwszy" in fake_anthropic.calls[0]["messages"][0]["content"]
    assert "Drugi" in fake_anthropic.calls[1]["messages"][0]["content"]


# ── OpenAI: system jako pierwsza wiadomość (automatyczny cache prefiksu) ──
def test_openai_wysyla_system_jako_pierwsza_wiadomosc(monkeypatch):
    openai = pytest.importorskip("openai")
    calls: list[dict] = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))],
            usage=SimpleNamespace(total_tokens=42),
        )

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(client_module, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai, "OpenAI", lambda **_: fake)

    provider = client_module._OpenAIProvider("gpt-test")
    _, tokens = provider.complete("STAŁA INSTRUKCJA", "artykuł", max_tokens=100)

    assert calls[0]["messages"] == [
        {"role": "system", "content": "STAŁA INSTRUKCJA"},
        {"role": "user", "content": "artykuł"},
    ]
    assert tokens == 42
