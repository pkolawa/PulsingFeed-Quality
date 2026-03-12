"""
Agregator wyników — łączy oceny deterministyczne i LLM w jeden wynik artykułu.

Wagi kategorii (config.py):
  faktyczność  30%  ← LLM
  językowa     20%  ← deterministyczna (LanguageTool + struktura)
  logika       20%  ← LLM
  dziennikarstwo 20% ← hybrid: 70% LLM + 30% deter. (sensacjonalizm)
  źródła       10%  ← deterministyczna
"""
import logging
from datetime import datetime, timezone
from typing import Any

from config import CATEGORY_WEIGHTS, ANALYSIS_VERSION

logger = logging.getLogger(__name__)


class ArticleScorer:
    """
    Łączy wyniki analizy deterministycznej i LLM w strukturę article_scores.
    """

    def compute(
        self,
        article_id: int,
        det: dict[str, Any],   # deterministic results
        llm: dict[str, Any],   # LLM results
    ) -> dict[str, Any]:

        # --- Wyniki kategorii ---
        factuality_score  = llm.get("factuality_score", 50.0)
        linguistic_score  = self._linguistic_combined(det)
        logic_score       = llm.get("logic_score", 50.0)
        journalism_score  = self._journalism_combined(
            llm.get("journalism_score", 50.0),
            det["sensationalism"]["score"],
        )
        sources_score     = det["sources"]["score"]

        # --- Wynik łączny ---
        total = (
            factuality_score  * CATEGORY_WEIGHTS["factuality"] +
            linguistic_score  * CATEGORY_WEIGHTS["linguistic"] +
            logic_score       * CATEGORY_WEIGHTS["logic"]      +
            journalism_score  * CATEGORY_WEIGHTS["journalism"] +
            sources_score     * CATEGORY_WEIGHTS["sources"]
        )

        logger.info(
            f"Artykuł #{article_id} | łączny: {total:.1f} "
            f"(fakt={factuality_score:.0f}, jęz={linguistic_score:.0f}, "
            f"log={logic_score:.0f}, dzien={journalism_score:.0f}, "
            f"źr={sources_score:.0f})"
        )

        return {
            "article_id":   article_id,

            # Wyniki (0–100)
            "total_score":       round(total, 2),
            "factuality_score":  round(factuality_score, 2),
            "linguistic_score":  round(linguistic_score, 2),
            "logic_score":       round(logic_score, 2),
            "journalism_score":  round(journalism_score, 2),
            "sources_score":     round(sources_score, 2),

            # Opisy
            "factuality_description":  llm.get("factuality_description", ""),
            "linguistic_description":  self._linguistic_description(det),
            "logic_description":       llm.get("logic_description", ""),
            "journalism_description":  self._journalism_description(llm, det),
            "sources_description":     det["sources"]["description"],
            "overall_description":     llm.get("overall_description", ""),

            # Dane surowe do debugowania
            "deterministic_data": det,
            "llm_data":           llm,

            # Metadane
            "llm_model":          llm.get("model", "unknown"),
            "analysis_version":   ANALYSIS_VERSION,
            "analyzed_at":        datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Pomocnicze metody łączenia wyników
    # ------------------------------------------------------------------

    def _linguistic_combined(self, det: dict) -> float:
        """
        Wynik językowy = 70% LanguageTool + 20% struktura + 10% brak sensacjonalizmu.
        """
        return (
            det["linguistic"]["score"]    * 0.70 +
            det["structure"]["score"]     * 0.20 +
            det["sensationalism"]["score"] * 0.10
        )

    def _journalism_combined(
        self, llm_journalism: float, sensationalism_quality: float
    ) -> float:
        """Dziennikarstwo = 70% LLM + 30% deter. ocena sensacjonalizmu."""
        return llm_journalism * 0.70 + sensationalism_quality * 0.30

    def _linguistic_description(self, det: dict) -> str:
        parts = [
            det["linguistic"]["description"],
            det["structure"]["description"],
        ]
        return " ".join(p for p in parts if p)

    def _journalism_description(self, llm: dict, det: dict) -> str:
        parts = [
            llm.get("journalism_description", ""),
            det["sensationalism"]["description"],
        ]
        return " ".join(p for p in parts if p)
