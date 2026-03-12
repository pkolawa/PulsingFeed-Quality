"""
PulsingFeed Quality — Worker analizy artykułów.

Uruchamia pętlę, która:
  1. Pobiera oczekujące artykuły z bazy (batch)
  2. Analizuje każdy przez pipeline deterministyczny + LLM
  3. Zapisuje wyniki do bazy
  4. Czeka WORKER_POLL_INTERVAL sekund i powtarza
"""
import logging
import signal
import time
import sys

from analyzer.pipeline import ArticleAnalysisPipeline
from db.repository     import Repository
from config            import WORKER_POLL_INTERVAL, WORKER_BATCH_SIZE

# --- Konfiguracja logowania ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("worker")


class Worker:
    def __init__(self) -> None:
        self.running  = True
        self.pipeline = ArticleAnalysisPipeline()
        self.repo     = Repository()
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT,  self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        logger.info(f"Sygnał {signum} — zatrzymuję worker...")
        self.running = False

    def run(self) -> None:
        logger.info(
            f"Worker uruchomiony | "
            f"batch={WORKER_BATCH_SIZE} | "
            f"poll={WORKER_POLL_INTERVAL}s"
        )
        while self.running:
            try:
                articles = self.repo.get_pending_articles(WORKER_BATCH_SIZE)

                if not articles:
                    logger.debug("Brak nowych artykułów — czekam...")
                    time.sleep(WORKER_POLL_INTERVAL)
                    continue

                logger.info(f"Pobrano {len(articles)} artykuł(ów) do analizy.")

                for article in articles:
                    if not self.running:
                        break
                    try:
                        result = self.pipeline.analyze(article)
                        self.repo.save_score(result)
                    except Exception as exc:
                        logger.error(
                            f"Błąd analizy artykułu #{article['id']}: {exc}",
                            exc_info=True,
                        )
                        self.repo.mark_failed(article["id"], str(exc))

            except Exception as exc:
                logger.error(f"Błąd workera: {exc}", exc_info=True)
                time.sleep(WORKER_POLL_INTERVAL)

        logger.info("Worker zatrzymany.")
        self.pipeline.close()
        self.repo.close()


if __name__ == "__main__":
    Worker().run()
