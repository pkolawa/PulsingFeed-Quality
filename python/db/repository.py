"""
Warstwa dostępu do bazy danych dla workera Pythona.
Używa psycopg2 z blokadą optymistyczną (FOR UPDATE SKIP LOCKED),
aby wielu workerów mogło bezpiecznie działać równolegle.
"""
import json
import logging
from typing import Any

import psycopg2
import psycopg2.extras

from config import (
    DATABASE_URL,
    WORKER_MAX_RETRIES,
    WORKER_PROCESSING_TIMEOUT_MINUTES,
    WORKER_RETRY_DELAY_MINUTES,
)

logger = logging.getLogger(__name__)

# Limit długości zapisywanego komunikatu błędu
_MAX_ERROR_LENGTH = 2000


class Repository:
    """Operacje CRUD na tabelach articles i article_scores."""

    def __init__(self) -> None:
        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = False
        logger.info("[DB] Połączono z bazą danych.")

    # ------------------------------------------------------------------
    def get_pending_articles(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Pobiera `limit` artykułów do analizy, atomowo zmieniając ich status
        na 'processing'. Obejmuje artykuły 'pending' oraz 'failed', które nie
        wyczerpały limitu ponowień i odczekały WORKER_RETRY_DELAY_MINUTES.
        SKIP LOCKED zapewnia, że równoległe workery nie pobiorą tych samych rekordów.
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status       = 'processing',
                       processing_started_at = NOW()
                WHERE  id IN (
                    SELECT id
                    FROM   articles
                    WHERE  analysis_status = 'pending'
                       OR (
                            analysis_status = 'failed'
                        AND retry_count < %s
                        AND COALESCE(processing_started_at, '-infinity')
                            < NOW() - make_interval(mins => %s)
                       )
                    ORDER  BY collected_at ASC
                    LIMIT  %s
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, title, content, url, publisher_id, retry_count
                """,
                (WORKER_MAX_RETRIES, WORKER_RETRY_DELAY_MINUTES, limit),
            )
            self.conn.commit()
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    def save_score(self, score: dict[str, Any]) -> None:
        """Zapisuje wynik analizy; aktualizuje status artykułu na 'done'."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO article_scores (
                    article_id,       total_score,
                    factuality_score, linguistic_score,
                    logic_score,      journalism_score, sources_score,
                    overall_description,
                    factuality_description, linguistic_description,
                    logic_description,      journalism_description,
                    sources_description,
                    deterministic_data, llm_data,
                    llm_model,          analysis_version
                )
                VALUES (
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT (article_id) DO UPDATE SET
                    total_score             = EXCLUDED.total_score,
                    factuality_score        = EXCLUDED.factuality_score,
                    linguistic_score        = EXCLUDED.linguistic_score,
                    logic_score             = EXCLUDED.logic_score,
                    journalism_score        = EXCLUDED.journalism_score,
                    sources_score           = EXCLUDED.sources_score,
                    overall_description     = EXCLUDED.overall_description,
                    factuality_description  = EXCLUDED.factuality_description,
                    linguistic_description  = EXCLUDED.linguistic_description,
                    logic_description       = EXCLUDED.logic_description,
                    journalism_description  = EXCLUDED.journalism_description,
                    sources_description     = EXCLUDED.sources_description,
                    deterministic_data      = EXCLUDED.deterministic_data,
                    llm_data                = EXCLUDED.llm_data,
                    llm_model               = EXCLUDED.llm_model,
                    analysis_version        = EXCLUDED.analysis_version,
                    analyzed_at             = NOW()
                """,
                (
                    score["article_id"],       score["total_score"],
                    score["factuality_score"], score["linguistic_score"],
                    score["logic_score"],      score["journalism_score"],
                    score["sources_score"],
                    score["overall_description"],
                    score["factuality_description"], score["linguistic_description"],
                    score["logic_description"],      score["journalism_description"],
                    score["sources_description"],
                    json.dumps(score["deterministic_data"]),
                    json.dumps(score["llm_data"]),
                    score["llm_model"],  score["analysis_version"],
                ),
            )
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status = 'done', error_message = NULL
                WHERE  id = %s
                """,
                (score["article_id"],),
            )
            self.conn.commit()
            logger.debug(f"[DB] Zapisano wyniki artykułu #{score['article_id']}.")

    # ------------------------------------------------------------------
    def mark_failed(self, article_id: int, error: str) -> None:
        """
        Oznacza artykuł jako 'failed', zwiększa licznik prób i zapisuje
        przyczynę. Dopóki retry_count < WORKER_MAX_RETRIES, artykuł wróci
        do kolejki po WORKER_RETRY_DELAY_MINUTES.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status = 'failed',
                       retry_count     = retry_count + 1,
                       error_message   = %s
                WHERE  id = %s
                RETURNING retry_count
                """,
                (error[:_MAX_ERROR_LENGTH], article_id),
            )
            row = cur.fetchone()
            self.conn.commit()

        retry_count = row[0] if row else 0
        if retry_count < WORKER_MAX_RETRIES:
            outcome = f"ponowienie za {WORKER_RETRY_DELAY_MINUTES} min"
        else:
            outcome = "limit ponowień wyczerpany"
        logger.warning(
            f"[DB] Artykuł #{article_id} oznaczony jako failed "
            f"(próba {retry_count}/{WORKER_MAX_RETRIES}, {outcome}): {error}"
        )

    # ------------------------------------------------------------------
    def release_stale_processing(self) -> int:
        """
        Odblokowuje artykuły porzucone w 'processing' (np. po awarii workera).
        Porzucenie liczy się jako nieudana próba — artykuł, który za każdym
        razem wywraca workera, nie zapętli się w nieskończoność.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status = 'failed',
                       retry_count     = retry_count + 1,
                       error_message   = 'Przetwarzanie przerwane (przekroczony czas)'
                WHERE  analysis_status = 'processing'
                  AND  COALESCE(processing_started_at, '-infinity')
                       < NOW() - make_interval(mins => %s)
                """,
                (WORKER_PROCESSING_TIMEOUT_MINUTES,),
            )
            released = cur.rowcount
            self.conn.commit()

        if released:
            logger.warning(f"[DB] Odblokowano {released} porzuconych artykułów z 'processing'.")
        return released

    # ------------------------------------------------------------------
    def release_articles(self, article_ids: list[int]) -> None:
        """Zwraca do kolejki pobrane, ale nieprzeanalizowane artykuły (np. przy zatrzymaniu)."""
        if not article_ids:
            return
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status = 'pending'
                WHERE  id = ANY(%s) AND analysis_status = 'processing'
                """,
                (article_ids,),
            )
            self.conn.commit()
        logger.info(f"[DB] Zwrócono {len(article_ids)} artykuł(ów) do kolejki.")

    # ------------------------------------------------------------------
    def close(self) -> None:
        self.conn.close()
        logger.info("[DB] Połączenie z bazą zamknięte.")
