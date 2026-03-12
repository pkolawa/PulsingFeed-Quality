"use strict";

const { Router } = require("express");

const SORT_MAP = {
  score:     "s.total_score DESC NULLS LAST",
  score_asc: "s.total_score ASC  NULLS LAST",
  date:      "a.collected_at DESC",
  date_asc:  "a.collected_at ASC",
};

module.exports = function articlesRouter(db) {
  const router = Router();

  // ── GET /api/articles ───────────────────────────────────────────────
  // Lista artykułów z wynikami; opcjonalne filtrowanie po publisher_id
  router.get("/", async (req, res) => {
    const {
      publisher_id,
      limit  = 30,
      offset = 0,
      sort   = "date",
      status,       // opcjonalny filtr statusu analizy
    } = req.query;

    const orderBy = SORT_MAP[sort] || SORT_MAP.date;
    const params  = [];
    const filters = [];

    if (publisher_id) {
      params.push(parseInt(publisher_id, 10));
      filters.push(`a.publisher_id = $${params.length}`);
    }
    if (status) {
      params.push(status);
      filters.push(`a.analysis_status = $${params.length}`);
    }

    const where = filters.length ? `WHERE ${filters.join(" AND ")}` : "";

    params.push(Math.min(parseInt(limit, 10), 100));
    params.push(Math.max(parseInt(offset, 10), 0));

    const limitPlaceholder  = `$${params.length - 1}`;
    const offsetPlaceholder = `$${params.length}`;

    try {
      const { rows } = await db.query(
        `SELECT
           a.id, a.title, a.url, a.published_at, a.collected_at,
           a.analysis_status, a.publisher_id,
           p.name                AS publisher_name,
           s.total_score,
           s.factuality_score,
           s.linguistic_score,
           s.logic_score,
           s.journalism_score,
           s.sources_score,
           s.overall_description
         FROM articles a
         JOIN publishers p ON p.id = a.publisher_id
         LEFT JOIN article_scores s ON s.article_id = a.id
         ${where}
         ORDER BY ${orderBy}
         LIMIT ${limitPlaceholder} OFFSET ${offsetPlaceholder}`,
        params
      );
      res.json(rows);
    } catch (err) {
      console.error("[API] GET /articles:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // ── GET /api/articles/:id ───────────────────────────────────────────
  // Pełne dane artykułu wraz z opisowymi wynikami wszystkich kategorii
  router.get("/:id", async (req, res) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return res.status(400).json({ error: "Nieprawidłowe ID." });

    try {
      const { rows } = await db.query(
        `SELECT
           a.id, a.title, a.url, a.content,
           a.published_at, a.collected_at, a.analysis_status,
           a.publisher_id,
           p.name        AS publisher_name,
           p.website_url AS publisher_website,
           s.total_score,
           s.factuality_score,
           s.linguistic_score,
           s.logic_score,
           s.journalism_score,
           s.sources_score,
           s.overall_description,
           s.factuality_description,
           s.linguistic_description,
           s.logic_description,
           s.journalism_description,
           s.sources_description,
           s.deterministic_data,
           s.llm_data,
           s.llm_model,
           s.analysis_version,
           s.analyzed_at
         FROM articles a
         JOIN publishers p ON p.id = a.publisher_id
         LEFT JOIN article_scores s ON s.article_id = a.id
         WHERE a.id = $1`,
        [id]
      );

      if (!rows.length) {
        return res.status(404).json({ error: "Artykuł nie istnieje." });
      }
      res.json(rows[0]);
    } catch (err) {
      console.error("[API] GET /articles/:id:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  return router;
};
