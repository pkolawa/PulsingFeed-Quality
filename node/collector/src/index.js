"use strict";

require("dotenv").config();
const cron = require("node-cron");
const db   = require("./db");
const { fetchAllFeeds } = require("./rss");

const CRON_SCHEDULE = process.env.COLLECTOR_CRON || "*/15 * * * *"; // co 15 minut

async function main() {
  console.log("[Collector] Startuję...");

  // Pierwsze pobranie natychmiast po uruchomieniu
  await fetchAllFeeds(db);

  // Następnie cyklicznie wg harmonogramu
  cron.schedule(CRON_SCHEDULE, async () => {
    console.log("[Collector] Zaplanowane pobranie kanałów RSS...");
    await fetchAllFeeds(db);
  });

  console.log(`[Collector] Harmonogram aktywny (${CRON_SCHEDULE}).`);
}

main().catch((err) => {
  console.error("[Collector] Błąd krytyczny:", err);
  process.exit(1);
});
