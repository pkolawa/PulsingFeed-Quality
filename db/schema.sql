-- ============================================================
-- PulsingFeed Quality — Database Schema
-- ============================================================

-- PUBLISHERS
-- Każdy kanał RSS to jeden wydawca.
CREATE TABLE publishers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    rss_url     TEXT         NOT NULL UNIQUE,
    website_url TEXT,
    logo_url    TEXT,
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ARTICLES
-- Każdy artykuł pobrany z RSS.
CREATE TABLE articles (
    id              SERIAL PRIMARY KEY,
    publisher_id    INTEGER      NOT NULL REFERENCES publishers(id) ON DELETE CASCADE,
    title           TEXT         NOT NULL,
    content         TEXT         NOT NULL,
    url             TEXT         UNIQUE,
    published_at    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ  DEFAULT NOW(),
    analysis_status VARCHAR(20)  DEFAULT 'pending',
    CONSTRAINT chk_status CHECK (
        analysis_status IN ('pending', 'processing', 'done', 'failed')
    )
);

CREATE INDEX idx_articles_publisher    ON articles(publisher_id);
CREATE INDEX idx_articles_status       ON articles(analysis_status);
CREATE INDEX idx_articles_collected    ON articles(collected_at DESC);

-- ARTICLE SCORES
-- Wynik analizy dla jednego artykułu.
CREATE TABLE article_scores (
    id                      SERIAL PRIMARY KEY,
    article_id              INTEGER       NOT NULL UNIQUE REFERENCES articles(id) ON DELETE CASCADE,

    -- Łączny wynik (0–100)
    total_score             NUMERIC(5,2)  NOT NULL,

    -- Wyniki kategorii (0–100)
    factuality_score        NUMERIC(5,2),   -- Faktyczność        (waga 30%)
    linguistic_score        NUMERIC(5,2),   -- Poprawność językowa (waga 20%)
    logic_score             NUMERIC(5,2),   -- Logika i spójność   (waga 20%)
    journalism_score        NUMERIC(5,2),   -- Standardy dziennik. (waga 20%)
    sources_score           NUMERIC(5,2),   -- Rzetelność źródeł   (waga 10%)

    -- Opisy tekstowe (uzasadnienia ocen, po polsku)
    overall_description     TEXT,
    factuality_description  TEXT,
    linguistic_description  TEXT,
    logic_description       TEXT,
    journalism_description  TEXT,
    sources_description     TEXT,

    -- Dane surowe (JSON)
    deterministic_data      JSONB,   -- wyniki analizy deterministycznej
    llm_data                JSONB,   -- surowa odpowiedź LLM

    -- Metadane
    analyzed_at             TIMESTAMPTZ  DEFAULT NOW(),
    llm_model               VARCHAR(100),
    analysis_version        VARCHAR(20)
);

CREATE INDEX idx_scores_total ON article_scores(total_score DESC);

-- PUBLISHER STATS (VIEW)
-- Agregat statystyk wydawcy, zawsze aktualny.
CREATE VIEW publisher_stats AS
SELECT
    p.id                                AS publisher_id,
    p.name,
    p.rss_url,
    p.website_url,
    p.logo_url,
    p.created_at,

    COUNT(a.id)                         AS total_articles,
    COUNT(s.id)                         AS analyzed_articles,

    ROUND(AVG(s.total_score),      2)   AS avg_total_score,
    ROUND(AVG(s.factuality_score), 2)   AS avg_factuality,
    ROUND(AVG(s.linguistic_score), 2)   AS avg_linguistic,
    ROUND(AVG(s.logic_score),      2)   AS avg_logic,
    ROUND(AVG(s.journalism_score), 2)   AS avg_journalism,
    ROUND(AVG(s.sources_score),    2)   AS avg_sources,

    -- Percentyl jakości: odsetek artykułów z wynikiem >= 70
    ROUND(
        100.0 * COUNT(CASE WHEN s.total_score >= 70 THEN 1 END) /
        NULLIF(COUNT(s.id), 0),
    1) AS pct_high_quality,

    MAX(a.collected_at)                 AS last_article_at,

    -- Trend: średnia ostatnich 30 artykułów vs reszta
    ROUND((
        SELECT AVG(s2.total_score)
        FROM (
            SELECT s3.total_score
            FROM article_scores s3
            JOIN articles a3 ON a3.id = s3.article_id
            WHERE a3.publisher_id = p.id
            ORDER BY a3.collected_at DESC
            LIMIT 30
        ) s2
    ), 2) AS recent_avg_score

FROM publishers p
LEFT JOIN articles       a ON a.publisher_id = p.id
LEFT JOIN article_scores s ON s.article_id   = a.id
GROUP BY p.id, p.name, p.rss_url, p.website_url, p.logo_url, p.created_at;
