"use strict";

const { Router } = require("express");

module.exports = function publishersRouter(db) {
  const router = Router();

  // ── GET /api/publishers ─────────────────────────────────────────────
  // Lista wszystkich wydawców z zagregowanymi statystykami
  router.get("/", async (req, res) => {
    try {
      const { rows } = await db.query(
        `SELECT * FROM publisher_stats ORDER BY avg_total_score DESC NULLS LAST`
      );
      res.json(rows);
    } catch (err) {
      console.error("[API] GET /publishers:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // ── GET /api/publishers/:id ─────────────────────────────────────────
  // Szczegóły jednego wydawcy + rozkład wyników
  router.get("/:id", async (req, res) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return res.status(400).json({ error: "Nieprawidłowe ID." });

    try {
      const [statsRes, distRes, trendRes] = await Promise.all([
        // Podstawowe statystyki
        db.query("SELECT * FROM publisher_stats WHERE publisher_id = $1", [id]),

        // Rozkład wyników w przedziałach co 10 pkt
        db.query(
          `SELECT
             width_bucket(s.total_score, 0, 100, 10) AS bucket,
             CASE width_bucket(s.total_score, 0, 100, 10)
               WHEN 1  THEN '0–10'
               WHEN 2  THEN '10–20'
               WHEN 3  THEN '20–30'
               WHEN 4  THEN '30–40'
               WHEN 5  THEN '40–50'
               WHEN 6  THEN '50–60'
               WHEN 7  THEN '60–70'
               WHEN 8  THEN '70–80'
               WHEN 9  THEN '80–90'
               WHEN 10 THEN '90–100'
               ELSE        '100'
             END AS label,
             COUNT(*) AS count
           FROM articles a
           JOIN article_scores s ON s.article_id = a.id
           WHERE a.publisher_id = $1
           GROUP BY 1, 2
           ORDER BY 1`,
          [id]
        ),

        // Trend miesięczny — ostatnie 6 miesięcy
        db.query(
          `SELECT
             TO_CHAR(DATE_TRUNC('month', a.collected_at), 'YYYY-MM') AS month,
             ROUND(AVG(s.total_score), 2)                             AS avg_score,
             COUNT(*)                                                  AS articles
           FROM articles a
           JOIN article_scores s ON s.article_id = a.id
           WHERE a.publisher_id = $1
             AND a.collected_at >= NOW() - INTERVAL '6 months'
           GROUP BY 1
           ORDER BY 1`,
          [id]
        ),
      ]);

      if (!statsRes.rows.length) {
        return res.status(404).json({ error: "Wydawca nie istnieje." });
      }

      res.json({
        ...statsRes.rows[0],
        score_distribution: distRes.rows,
        monthly_trend:      trendRes.rows,
      });
    } catch (err) {
      console.error("[API] GET /publishers/:id:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // ── POST /api/publishers ────────────────────────────────────────────
  // Dodanie nowego wydawcy (kanału RSS)
  router.post("/", async (req, res) => {
    const { name, rss_url, website_url } = req.body;
    if (!name || !rss_url) {
      return res.status(400).json({ error: "Pola 'name' i 'rss_url' są wymagane." });
    }
    try {
      const { rows } = await db.query(
        `INSERT INTO publishers (name, rss_url, website_url)
         VALUES ($1, $2, $3) RETURNING *`,
        [name.trim(), rss_url.trim(), website_url?.trim() || null]
      );
      res.status(201).json(rows[0]);
    } catch (err) {
      if (err.code === "23505") {
        return res.status(409).json({ error: "Wydawca z tym URL RSS już istnieje." });
      }
      console.error("[API] POST /publishers:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // ── POST /api/publishers/:id/analyze ────────────────────────────────
  // Wymusza ponowną analizę artykułów wydawcy.
  // ?force=true  — resetuje wszystkie artykuły (także już przeanalizowane)
  // domyślnie    — resetuje tylko artykuły ze statusem 'failed'
  router.post("/:id/analyze", async (req, res) => {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return res.status(400).json({ error: "Nieprawidłowe ID." });

    const force = req.query.force === "true";
    const statusFilter = force
      ? ["pending", "processing", "done", "failed"]
      : ["failed"];

    try {
      const publisherRes = await db.query(
        "SELECT id, name FROM publishers WHERE id = $1",
        [id]
      );
      if (!publisherRes.rows.length) {
        return res.status(404).json({ error: "Wydawca nie istnieje." });
      }

      const { rows } = await db.query(
        `UPDATE articles
         SET analysis_status = 'pending'
         WHERE publisher_id = $1
           AND analysis_status = ANY($2::text[])
         RETURNING id`,
        [id, statusFilter]
      );

      console.log(
        `[API] Analiza wymuszona dla wydawcy #${id} — ${rows.length} artykuł(ów) ustawiono na 'pending'${force ? " (force)" : ""}`
      );

      res.json({
        publisher_id: id,
        publisher_name: publisherRes.rows[0].name,
        queued: rows.length,
        force,
      });
    } catch (err) {
      console.error("[API] POST /publishers/:id/analyze:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  // ── DELETE /api/publishers/:id ──────────────────────────────────────
  router.delete("/:id", async (req, res) => {
    try {
      await db.query("DELETE FROM publishers WHERE id = $1", [req.params.id]);
      res.json({ success: true });
    } catch (err) {
      console.error("[API] DELETE /publishers/:id:", err.message);
      res.status(500).json({ error: err.message });
    }
  });

  return router;
};
