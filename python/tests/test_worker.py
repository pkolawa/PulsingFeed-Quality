"""Testy pętli workera na atrapach bazy i pipeline'u: co trafia do bazy i co dzieje się przy błędach."""
import signal

import pytest

import main
from config import WORKER_BATCH_SIZE, WORKER_POLL_INTERVAL

OK_RESULT = {"llm_data": {"success": True}}


def article(article_id: int) -> dict:
    return {"id": article_id, "title": f"Artykuł {article_id}", "content": "Treść"}


class FakeRepository:
    """Wydaje kolejne partie; po ostatniej zatrzymuje workera, żeby pętla się skończyła."""

    def __init__(self):
        self.batches: list = []
        self.saved: list = []
        self.failed: list = []
        self.released: list = []
        self.limits: list = []
        self.stale_calls = 0
        self.closed = False
        self.worker = None

    def get_pending_articles(self, limit):
        self.limits.append(limit)
        if not self.batches:
            self.worker.running = False
            return []
        batch = self.batches.pop(0)
        if isinstance(batch, Exception):
            raise batch
        return batch

    def save_score(self, score):
        self.saved.append(score)

    def mark_failed(self, article_id, error):
        self.failed.append((article_id, error))

    def release_articles(self, article_ids):
        self.released.append(article_ids)

    def release_stale_processing(self):
        self.stale_calls += 1
        return 0

    def close(self):
        self.closed = True


class FakePipeline:
    """Zwraca wynik według id artykułu; wyjątek z mapy zostaje rzucony."""

    def __init__(self):
        self.results: dict = {}
        self.analyzed: list = []
        self.on_analyze = None
        self.closed = False

    def analyze(self, art):
        self.analyzed.append(art["id"])
        if self.on_analyze:
            self.on_analyze()
        result = self.results.get(art["id"], {**OK_RESULT, "article_id": art["id"]})
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


@pytest.fixture
def sleeps(monkeypatch) -> list:
    calls: list = []
    monkeypatch.setattr(main.time, "sleep", calls.append)
    return calls


@pytest.fixture
def worker(monkeypatch, sleeps) -> main.Worker:
    monkeypatch.setattr(main, "Repository", FakeRepository)
    monkeypatch.setattr(main, "ArticleAnalysisPipeline", FakePipeline)
    # Worker rejestruje handlery sygnałów; nie zostawiamy ich w procesie pytesta
    monkeypatch.setattr(main.signal, "signal", lambda *_: None)
    instance = main.Worker()
    instance.repo.worker = instance
    return instance


# ── Zapis wyniku ─────────────────────────────────────────────────────
def test_udana_analiza_zapisuje_wynik(worker):
    worker.repo.batches = [[article(1), article(2)]]
    worker.run()

    assert [s["article_id"] for s in worker.repo.saved] == [1, 2]
    assert worker.repo.failed == []


def test_pobiera_partie_o_skonfigurowanym_rozmiarze(worker):
    worker.run()
    assert worker.repo.limits == [WORKER_BATCH_SIZE]


def test_nieudany_llm_oznacza_failed_zamiast_zapisu(worker):
    worker.repo.batches = [[article(1)]]
    worker.pipeline.results[1] = {"llm_data": {"success": False, "error": "timeout"}}
    worker.run()

    assert worker.repo.saved == []
    assert worker.repo.failed == [(1, "LLM: timeout")]


def test_nieudany_llm_bez_opisu_bledu(worker):
    worker.repo.batches = [[article(1)]]
    worker.pipeline.results[1] = {"llm_data": {}}
    worker.run()

    assert worker.repo.saved == []
    assert worker.repo.failed == [(1, "LLM: Analiza LLM nieudana")]


def test_nieudany_llm_nie_przerywa_partii(worker):
    worker.repo.batches = [[article(1), article(2)]]
    worker.pipeline.results[1] = {"llm_data": {"success": False, "error": "timeout"}}
    worker.run()

    assert [s["article_id"] for s in worker.repo.saved] == [2]


# ── Błędy ────────────────────────────────────────────────────────────
def test_wyjatek_analizy_oznacza_failed_i_nie_przerywa_partii(worker):
    worker.repo.batches = [[article(1), article(2)]]
    worker.pipeline.results[1] = ValueError("zepsuty artykuł")
    worker.run()

    assert worker.repo.failed == [(1, "zepsuty artykuł")]
    assert [s["article_id"] for s in worker.repo.saved] == [2]


def test_blad_bazy_czeka_i_ponawia(worker, sleeps):
    worker.repo.batches = [ConnectionError("baza leży"), [article(1)]]
    worker.run()

    # Pierwsze czekanie po błędzie, drugie w bezczynności po wyczerpaniu kolejki
    assert sleeps == [WORKER_POLL_INTERVAL, WORKER_POLL_INTERVAL]
    assert [s["article_id"] for s in worker.repo.saved] == [1]


# ── Bezczynność i porzucone artykuły ─────────────────────────────────
def test_start_zwalnia_porzucone_artykuly(worker):
    worker.repo.batches = [[article(1)]]
    stale_before_fetch = []
    fetch = worker.repo.get_pending_articles

    def spy(limit):
        stale_before_fetch.append(worker.repo.stale_calls)
        return fetch(limit)

    worker.repo.get_pending_articles = spy
    worker.run()

    assert stale_before_fetch[0] == 1


def test_bezczynnosc_zwalnia_porzucone_i_czeka(worker, sleeps):
    worker.run()
    assert worker.repo.stale_calls == 2
    assert sleeps == [WORKER_POLL_INTERVAL]


# ── Zatrzymanie ──────────────────────────────────────────────────────
def test_zatrzymanie_w_trakcie_partii_oddaje_reszte(worker):
    worker.repo.batches = [[article(1), article(2), article(3)]]

    def stop():
        worker.running = False

    worker.pipeline.on_analyze = stop
    worker.run()

    # Bieżący artykuł kończymy, pozostałe wracają do kolejki
    assert worker.pipeline.analyzed == [1]
    assert [s["article_id"] for s in worker.repo.saved] == [1]
    assert worker.repo.released == [[2, 3]]


def test_sygnal_zatrzymuje_petle(worker):
    worker._handle_signal(signal.SIGTERM, None)
    assert worker.running is False


def test_koniec_pracy_zamyka_zasoby(worker):
    worker.run()
    assert worker.repo.closed is True
    assert worker.pipeline.closed is True
