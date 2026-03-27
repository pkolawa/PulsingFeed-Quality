"use strict";

const { JSDOM }      = require("jsdom");
const { Readability } = require("@mozilla/readability");

const FETCH_TIMEOUT_MS = 10_000;
const MIN_CONTENT_LENGTH = 300;

/**
 * Pobiera pełną treść artykułu spod podanego URL.
 * Używa Readability (Firefox Reader View) do ekstrakcji tekstu.
 *
 * @param {string} url
 * @returns {Promise<string|null>} Czysty tekst artykułu lub null przy błędzie/zbyt krótkiej treści
 */
async function scrapeFullText(url) {
  let html;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (compatible; PulsingFeed-Quality-Bot/1.0; +https://github.com/pulsingfeed)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pl,en;q=0.9",
      },
    });
    clearTimeout(timer);

    if (!response.ok) return null;
    html = await response.text();
  } catch {
    return null;
  }

  try {
    const dom = new JSDOM(html, { url });
    const reader = new Readability(dom.window.document);
    const article = reader.parse();

    if (!article || !article.textContent) return null;

    const text = article.textContent.replace(/\s+/g, " ").trim();
    return text.length >= MIN_CONTENT_LENGTH ? text : null;
  } catch {
    return null;
  }
}

module.exports = { scrapeFullText };
