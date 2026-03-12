"use strict";

require("dotenv").config();
const express    = require("express");
const cors       = require("cors");
const db         = require("./db");
const publishers = require("./routes/publishers");
const articles   = require("./routes/articles");

const app  = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// ── Trasy ──────────────────────────────────────────────────────────────
app.use("/api/publishers", publishers(db));
app.use("/api/articles",   articles(db));

// Healthcheck
app.get("/api/health", (_req, res) =>
  res.json({ status: "ok", timestamp: new Date().toISOString() })
);

// 404
app.use((_req, res) => res.status(404).json({ error: "Zasób nie istnieje." }));

// Globalny handler błędów
app.use((err, _req, res, _next) => {
  console.error("[API] Unhandled error:", err);
  res.status(500).json({ error: "Wewnętrzny błąd serwera." });
});

app.listen(PORT, () => {
  console.log(`[API] Serwer działa na http://localhost:${PORT}`);
});
