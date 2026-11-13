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
    "anthropic": "claude-sonnet-5-5",
    "openai":    "gpt-4o-mini",
}
# `or` zamiast domyślnej wartości getenv — docker-compose przekazuje pusty
# string, gdy zmienna nie jest ustawiona w .env
LLM_MODEL: str = os.getenv("LLM_MODEL") or _DEFAULT_MODELS.get(LLM_PROVIDER, "claude-sonnet-5-5")

# Głębokość rozumowania modelu Claude: low | medium | high | xhigh | max
ANTHROPIC_EFFORT: str = os.getenv("ANTHROPIC_EFFORT") or "medium"

# --- Worker ---
WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "10"))
WORKER_BATCH_SIZE: int    = int(os.getenv("WORKER_BATCH_SIZE", "5"))
# Ile razy ponawiać analizę artykułu, zanim zostanie trwale 'failed'
WORKER_MAX_RETRIES: int   = int(os.getenv("WORKER_MAX_RETRIES", "3"))
# Odstęp między ponowieniami (chroni przed spalaniem prób, gdy API LLM leży)
WORKER_RETRY_DELAY_MINUTES: int = int(os.getenv("WORKER_RETRY_DELAY_MINUTES", "30"))
# Po tym czasie artykuł w 'processing' uznajemy za porzucony (np. awaria workera)
WORKER_PROCESSING_TIMEOUT_MINUTES: int = int(os.getenv("WORKER_PROCESSING_TIMEOUT_MINUTES", "30"))

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
