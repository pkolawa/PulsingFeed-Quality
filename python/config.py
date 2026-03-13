"""
Konfiguracja aplikacji — wartości pobierane ze zmiennych środowiskowych.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Baza danych ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/pulsingfeed"
)

# --- LLM ---
# Dostępne wartości: "anthropic" | "openai"
LLM_PROVIDER: str      = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str    = os.getenv("OPENAI_API_KEY", "")

# Domyślny model zależy od wybranego dostawcy
_DEFAULT_MODELS = {
    "anthropic": "claude-3-5-haiku-20241022",
    "openai":    "gpt-4o-mini",
}
LLM_MODEL: str = os.getenv("LLM_MODEL", _DEFAULT_MODELS.get(LLM_PROVIDER, "claude-3-5-haiku-20241022"))

# --- Worker ---
WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "10"))
WORKER_BATCH_SIZE: int    = int(os.getenv("WORKER_BATCH_SIZE", "5"))

# --- Wersja algorytmu (zmień przy każdej znaczącej zmianie logiki) ---
ANALYSIS_VERSION: str = "1.0.0"

# --- Wagi kategorii (suma = 1.0) ---
CATEGORY_WEIGHTS: dict[str, float] = {
    "factuality":  0.30,   # Faktyczność
    "linguistic":  0.20,   # Poprawność językowa
    "logic":       0.20,   # Logika i spójność
    "journalism":  0.20,   # Standardy dziennikarskie
    "sources":     0.10,   # Rzetelność źródeł
}
