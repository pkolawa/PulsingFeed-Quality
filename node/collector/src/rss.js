"use strict";

const Parser = require("rss-parser");
const { JSDOM } = require("jsdom");

const parser = new Parser({
  timeout: 15_000,
  headers: { "User-Agent": "PulsingFeed-Quality-Bot/1.0 (+https://github.com/pulsingfeed)" },
  customFields: {
    item: [["content:encoded", "contentEncoded"]],
  },
});

// ---------------------------------------------------------------------------
// Funkcje pomocnicze
// ---------------------------------------------------------------------------

/**
 * Usuwa tagi HTML z tekstu i normalizuje białe znaki.
 * Używa JSDOM dla dokładnego parsowania; fallback to regex.
 */
function stripHtml(html) {
  if (!html) return "";
  try {
    const dom = new JSDOM(html);
    return (dom.window.document.body.textContent || "")
      .replace(/\s+/g, " ")
      .trim();
  } catch {
    return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }
}

/**
 * Wybiera najlepszą treść spośród dostępnych pól RSS.
 */
function extractContent(item) {
  const raw =
    item.contentEncoded ||
    item.content ||
    item["content:encoded"] ||
    item.contentSnippet ||
    item.summary ||
    "";
  return stripHtml(raw);
}

// ---------------------------------------------------------------------------
// Pobieranie jednego kanału
// ---------------------------------------------------------------------------

/**
 * @param {object} publisher  – wiersz z tabeli publishers {id, name, rss_url}
 * @param {object} db         – pula połączeń pg
 * @returns {Promise<number>} – liczba dodanych artykułów
 */
async function fetchFeed(publisher, db) {
  let feed;
  try {
    feed = await parser.parseURL(publisher.rss_url);
  } catch (err) {
    console.error(`[Collector] Błąd pobierania «${publisher.name}»: ${err.message}`);
    return 0;
  }

  let newCount = 0;

  for (const item of feed.items) {
    const title      = (item.title || "").trim();
    const content    = extractContent(item);
    const url        = item.link || item.guid || null;
    const publishedAt = item.pubDate ? new Date(item.pubDate) : null;

    // Pomijamy artykuły bez treści lub zbyt krótkie
    if (!title || content.length < 120) continue;

    try {
      const result = await db.query(
        `INSERT INTO articles (publisher_id, title, content, url, published_at)
         VALUES ($1, $2, $3, $4, $5)
         ON CONFLICT (url) DO NOTHING`,
        [publisher.id, title, content, url, publishedAt]
      );
      if (result.rowCount > 0) newCount++;
    } catch (err) {
      if (!err.message.includes("unique")) {
        console.error(`[Collector] Błąd DB dla ${url}: ${err.message}`);
      }
    }
  }

  if (newCount > 0) {
    console.log(`[Collector] «${publisher.name}» → +${newCount} nowych artykułów`);
  }

  return newCount;
}

// ---------------------------------------------------------------------------
// Pobieranie wszystkich kanałów
// ---------------------------------------------------------------------------

/**
 * Pobiera artykuły ze wszystkich aktywnych wydawców (równolegle).
 */
async function fetchAllFeeds(db) {
  const { rows: publishers } = await db.query(
    "SELECT id, name, rss_url FROM publishers ORDER BY id"
  );

  if (publishers.length === 0) {
    console.log("[Collector] Brak wydawców w bazie. Dodaj ich przez API.");
    return;
  }

  console.log(`[Collector] Pobieram ${publishers.length} kanał(ów) RSS...`);

  const results = await Promise.allSettled(
    publishers.map((p) => fetchFeed(p, db))
  );

  const total = results.reduce(
    (sum, r) => sum + (r.status === "fulfilled" ? r.value : 0),
    0
  );
  console.log(`[Collector] Gotowe — łącznie +${total} nowych artykułów.`);
}

module.exports = { fetchAllFeeds };
