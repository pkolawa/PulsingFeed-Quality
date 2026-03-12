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
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")

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
