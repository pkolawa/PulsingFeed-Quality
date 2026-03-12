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

from config import DATABASE_URL

logger = logging.getLogger(__name__)


class Repository:
    """Operacje CRUD na tabelach articles i article_scores."""

    def __init__(self) -> None:
        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = False
        logger.info("[DB] Połączono z bazą danych.")

    # ------------------------------------------------------------------
    def get_pending_articles(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Pobiera `limit` artykułów ze statusem 'pending', atomowo
        zmieniając ich status na 'processing'.
        SKIP LOCKED zapewnia, że równoległe workery nie pobiorą tych samych rekordów.
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE articles
                SET    analysis_status = 'processing'
                WHERE  id IN (
                    SELECT id
                    FROM   articles
                    WHERE  analysis_status = 'pending'
                    ORDER  BY collected_at ASC
                    LIMIT  %s
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, title, content, url, publisher_id
                """,
                (limit,),
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
                "UPDATE articles SET analysis_status = 'done' WHERE id = %s",
                (score["article_id"],),
            )
            self.conn.commit()
            logger.debug(f"[DB] Zapisano wyniki artykułu #{score['article_id']}.")

    # ------------------------------------------------------------------
    def mark_failed(self, article_id: int, error: str) -> None:
        """Oznacza artykuł jako 'failed' po niepowodzeniu analizy."""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE articles SET analysis_status = 'failed' WHERE id = %s",
                (article_id,),
            )
            self.conn.commit()
        logger.warning(f"[DB] Artykuł #{article_id} oznaczony jako failed: {error}")

    # ------------------------------------------------------------------
    def close(self) -> None:
        self.conn.close()
        logger.info("[DB] Połączenie z bazą zamknięte.")
