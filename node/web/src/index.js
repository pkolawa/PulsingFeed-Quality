"use strict";

require("dotenv").config();
const express = require("express");
const axios   = require("axios");
const path    = require("path");

const app     = express();
const PORT    = process.env.PORT    || 3000;
const API_URL = process.env.API_URL || "http://localhost:3001";

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.static(path.join(__dirname, "../public")));

// Pomocnicze: oblicz klasę gradientu na podstawie wyniku
function scoreGrade(score) {
  if (score === null || score === undefined) return "na";
  if (score >= 80) return "a";
  if (score >= 65) return "b";
  if (score >= 50) return "c";
  return "d";
}

// Pomocnicze: formatuj datę
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pl-PL", {
    year: "numeric", month: "short", day: "numeric",
  });
}

// ── Strona główna: lista wydawców ────────────────────────────────────
app.get("/", async (req, res) => {
  try {
    const { data: publishers } = await axios.get(`${API_URL}/api/publishers`);
    res.render("index", { publishers, scoreGrade, fmtDate });
  } catch (err) {
    res.render("error", { message: err.message });
  }
});

// ── Szczegóły wydawcy ────────────────────────────────────────────────
app.get("/publisher/:id", async (req, res) => {
  try {
    const [{ data: publisher }, { data: articles }] = await Promise.all([
      axios.get(`${API_URL}/api/publishers/${req.params.id}`),
      axios.get(`${API_URL}/api/articles?publisher_id=${req.params.id}&limit=50&sort=score`),
    ]);
    res.render("publisher", { publisher, articles, scoreGrade, fmtDate });
  } catch (err) {
    res.render("error", { message: err.message });
  }
});

// ── Szczegóły artykułu ───────────────────────────────────────────────
app.get("/article/:id", async (req, res) => {
  try {
    const { data: article } = await axios.get(`${API_URL}/api/articles/${req.params.id}`);
    res.render("article", { article, scoreGrade, fmtDate });
  } catch (err) {
    res.render("error", { message: err.message });
  }
});

// 404
app.use((_req, res) => res.status(404).render("error", { message: "Strona nie istnieje." }));

app.listen(PORT, () => {
  console.log(`[Web] Aplikacja działa na http://localhost:${PORT}`);
});
