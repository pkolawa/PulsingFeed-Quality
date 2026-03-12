"""
Główny potok analizy artykułu.

Sekwencja:
  1. Analiza deterministyczna (językowa, strukturalna, źródłowa, sensacjonalizm)
  2. Analiza LLM (faktyczność, logika, standardy dziennikarskie)
  3. Agregacja wyników (scorer)
"""
import logging
from typing import Any

from .deterministic.linguistic    import LinguisticAnalyzer
from .deterministic.structure     import StructureAnalyzer
from .deterministic.sources       import SourcesAnalyzer
from .deterministic.sensationalism import SensationalismAnalyzer
from .llm.evaluator               import LLMEvaluator
from .scorer                      import ArticleScorer

logger = logging.getLogger(__name__)


class ArticleAnalysisPipeline:
    """Orkiestrator całego procesu oceny jednego artykułu."""

    def __init__(self) -> None:
        self.linguistic    = LinguisticAnalyzer()
        self.structure     = StructureAnalyzer()
        self.sources       = SourcesAnalyzer()
        self.sensationalism = SensationalismAnalyzer()
        self.llm           = LLMEvaluator()
        self.scorer        = ArticleScorer()

    def analyze(self, article: dict[str, Any]) -> dict[str, Any]:
        """
        Przeprowadza pełną analizę artykułu.

        Parameters
        ----------
        article : dict z kluczami id, title, content, publisher_id

        Returns
        -------
        dict gotowy do zapisu w tabeli article_scores
        """
        article_id = article["id"]
        title      = (article.get("title") or "").strip()
        content    = (article.get("content") or "").strip()

        logger.info(f"[Pipeline] Start → artykuł #{article_id}: «{title[:60]}»")

        # ── Krok 1: Analiza deterministyczna ────────────────────────────
        logger.debug(f"[Pipeline] #{article_id} — analiza deterministyczna")
        det_results: dict[str, Any] = {
            "linguistic":    self.linguistic.analyze(content, title),
            "structure":     self.structure.analyze(content, title),
            "sources":       self.sources.analyze(content),
            "sensationalism": self.sensationalism.analyze(content, title),
        }

        # ── Krok 2: Analiza LLM ─────────────────────────────────────────
        logger.debug(f"[Pipeline] #{article_id} — analiza LLM")
        llm_results = self.llm.evaluate(title, content)

        # ── Krok 3: Agregacja ───────────────────────────────────────────
        final = self.scorer.compute(article_id, det_results, llm_results)

        logger.info(
            f"[Pipeline] #{article_id} zakończony — wynik: {final['total_score']:.1f}/100"
        )
        return final

    def close(self) -> None:
        """Zwalnia zasoby (m.in. instancję LanguageTool)."""
        self.linguistic.close()
        logger.info("[Pipeline] Zasoby zwolnione.")
