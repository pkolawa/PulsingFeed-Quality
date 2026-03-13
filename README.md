# PulsingFeed Quality

System analizy jakości treści dziennikarskich. Zbiera artykuły z RSS, ocenia je deterministycznie (gramatyka, struktura, sensacjonalizm, źródła) oraz za pomocą LLM (faktyczność, logika, standardy dziennikarskie) i prezentuje wyniki w rankingu wydawców.

## Architektura

```
Quality/
├── python/          # Worker analizy (LanguageTool + Claude API)
├── node/
│   ├── collector/   # Kolektor RSS (cron co 15 min)
│   ├── api/         # REST API (port 3001)
│   └── web/         # Web UI (port 3000)
├── db/
│   └── schema.sql   # Schemat PostgreSQL
├── docker-compose.yml
└── .env.example
```

## Wymagania

- **Produkcja:** Docker + Docker Compose
- **Development:**
  - Node.js 20+
  - Python 3.12+
  - Java (wymagane przez LanguageTool)
  - PostgreSQL 16+

---

## Środowisko developerskie

### 1. Konfiguracja zmiennych środowiskowych

```bash
cp .env.example .env
```

Uzupełnij `.env`:

```env
# Baza danych
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pulsingfeed

# Anthropic API (wymagane do analizy LLM)
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022

# Worker
WORKER_POLL_INTERVAL=10   # sekundy między kolejkami
WORKER_BATCH_SIZE=5       # artykułów na jedno przejście

# Porty serwisów Node.js
COLLECTOR_PORT=3002
API_PORT=3001
WEB_PORT=3000
API_URL=http://localhost:3001
```

### 2. Uruchomienie bazy danych (PostgreSQL przez Docker)

```bash
docker run -d \
  --name pulsingfeed-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=pulsingfeed \
  -p 5432:5432 \
  postgres:16-alpine
```

Zaaplikowanie schematu:

```bash
psql postgresql://postgres:postgres@localhost:5432/pulsingfeed -f db/schema.sql
```

### 3. Python Worker

```bash
cd python

# Utwórz wirtualne środowisko
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Zainstaluj zależności (wymaga Javy w PATH)
pip install -r requirements.txt

# Uruchom workera
python main.py
```

> **Uwaga:** Pierwsze uruchomienie pobiera modele LanguageTool (~200 MB). Kolejne starty są szybsze.

### 4. Kolektor RSS

```bash
cd node/collector

npm install
npm run dev        # nodemon — auto-restart przy zmianach
# lub
npm start          # bez auto-restartu
```

### 5. API

```bash
cd node/api

npm install
npm run dev
# lub
npm start
```

Dostępne pod: `http://localhost:3001`

### 6. Web UI

```bash
cd node/web

npm install
npm run dev
# lub
npm start
```

Dostępne pod: `http://localhost:3000`

---

## Środowisko produkcyjne (Docker Compose)

### Uruchomienie całego stosu

```bash
# Skopiuj i uzupełnij zmienne środowiskowe
cp .env.example .env
# Edytuj .env — ustaw ANTHROPIC_API_KEY

# Zbuduj obrazy i uruchom serwisy
docker compose up -d

# Sprawdź status kontenerów
docker compose ps
```

### Zatrzymanie

```bash
docker compose down
```

### Zatrzymanie z usunięciem danych (baza danych)

```bash
docker compose down -v
```

### Przebudowanie obrazów (po zmianach w kodzie)

```bash
docker compose build
docker compose up -d
```

Lub jednym poleceniem:

```bash
docker compose up -d --build
```

### Aktualizacja wybranego serwisu

```bash
docker compose build python-worker
docker compose up -d python-worker
```

---

## Porty i adresy

| Serwis       | Adres lokalny             | Opis                          |
|--------------|---------------------------|-------------------------------|
| Web UI       | http://localhost:3000     | Ranking wydawców i artykułów  |
| API          | http://localhost:3001     | REST API                      |
| PostgreSQL   | localhost:5432            | Baza danych                   |

---

## API — dostępne endpointy

```
GET    /api/publishers              # Lista wydawców posortowana wg jakości
GET    /api/publishers/:id          # Szczegóły wydawcy + trend 6-miesięczny
POST   /api/publishers              # Dodanie nowego źródła RSS
DELETE /api/publishers/:id          # Usunięcie wydawcy
POST   /api/publishers/:id/analyze  # Wymuszenie analizy artykułów wydawcy

GET    /api/articles                # Lista artykułów (z filtrowaniem)
GET    /api/articles/:id            # Szczegóły artykułu + pełne oceny

GET    /api/health                  # Healthcheck
```

### Dodanie wydawcy

```bash
curl -X POST http://localhost:3001/api/publishers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TVN24",
    "rss_url": "https://tvn24.pl/najnowsze.xml",
    "website_url": "https://tvn24.pl"
  }'
```

### Wymuszenie analizy artykułów wydawcy

Endpoint ustawia artykuły wybranego wydawcy z powrotem na status `pending`, dzięki czemu Python worker podejmie ich analizę w kolejnym cyklu (domyślnie co 10 sekund).

```bash
# Ponów analizę artykułów które zakończyły się błędem (status: failed)
curl -X POST http://localhost:3001/api/publishers/1/analyze

# Wymuś pełną re-analizę wszystkich artykułów wydawcy (także już przeanalizowanych)
curl -X POST "http://localhost:3001/api/publishers/1/analyze?force=true"
```

**Parametry:**

| Parametr     | Typ     | Domyślnie | Opis                                                              |
|--------------|---------|-----------|-------------------------------------------------------------------|
| `id`         | integer | —         | ID wydawcy (z `GET /api/publishers`)                              |
| `force=true` | boolean | `false`   | Jeśli `true` — resetuje również artykuły ze statusem `done`      |

**Odpowiedź:**

```json
{
  "publisher_id": 1,
  "publisher_name": "TVN24",
  "queued": 47,
  "force": false
}
```

**Przypadki użycia:**
- `force=false` (domyślnie) — ponów analizę dla artykułów które się nie powiodły (`failed`)
- `force=true` — pełna re-analiza po zmianie wag scoring'u lub aktualizacji promptów LLM

---

## Logi

```bash
# Wszystkie serwisy (Docker Compose)
docker compose logs -f

# Wybrany serwis
docker compose logs -f python-worker
docker compose logs -f collector
docker compose logs -f api
docker compose logs -f web
```

---

## Baza danych — przydatne komendy

```bash
# Połączenie z bazą (Docker Compose)
docker compose exec postgres psql -U postgres -d pulsingfeed

# Połączenie lokalne (dev)
psql postgresql://postgres:postgres@localhost:5432/pulsingfeed
```

Przydatne zapytania:

```sql
-- Status kolejki artykułów
SELECT analysis_status, COUNT(*) FROM articles GROUP BY analysis_status;

-- Ranking wydawców
SELECT name, avg_total_score, analyzed_articles FROM publisher_stats ORDER BY avg_total_score DESC;

-- Ostatnio przeanalizowane artykuły
SELECT a.title, s.total_score, s.analyzed_at
FROM articles a
JOIN article_scores s ON s.article_id = a.id
ORDER BY s.analyzed_at DESC
LIMIT 20;
```

---

## Konfiguracja workera

Zmienne w `.env` kontrolujące zachowanie workera Python:

| Zmienna               | Domyślna | Opis                                    |
|-----------------------|----------|-----------------------------------------|
| `WORKER_POLL_INTERVAL` | `10`    | Sekundy między sprawdzeniem kolejki     |
| `WORKER_BATCH_SIZE`    | `5`     | Liczba artykułów analizowanych naraz    |
| `LLM_MODEL`            | `claude-3-5-haiku-20241022` | Model Claude do analizy |
| `ANALYSIS_VERSION`     | `1.0.0` | Wersja algorytmu (w `config.py`)        |

---

## Rozwiązywanie problemów

### Worker nie startuje — brak Javy

```bash
# macOS
brew install openjdk

# Ubuntu/Debian
sudo apt install default-jre-headless
```

### Błąd połączenia z bazą danych

Sprawdź, czy PostgreSQL działa i `DATABASE_URL` jest poprawne:

```bash
psql $DATABASE_URL -c "SELECT 1"
```

### Artykuły nie są analizowane (status `pending` nie zmienia się)

1. Sprawdź logi workera: `docker compose logs -f python-worker`
2. Zweryfikuj klucz API: `echo $ANTHROPIC_API_KEY`
3. Sprawdź kolejkę: `SELECT analysis_status, COUNT(*) FROM articles GROUP BY analysis_status;`

### Kolektor nie zbiera artykułów

1. Sprawdź logi: `docker compose logs -f collector`
2. Upewnij się, że w bazie są wydawcy: `SELECT * FROM publishers;`
3. Sprawdź dostępność źródeł RSS (timeout, SSL)

### Reset bazy danych (dev)

```bash
psql postgresql://postgres:postgres@localhost:5432/pulsingfeed -c "
  DROP TABLE IF EXISTS article_scores, articles, publishers CASCADE;
  DROP VIEW IF EXISTS publisher_stats;
"
psql postgresql://postgres:postgres@localhost:5432/pulsingfeed -f db/schema.sql
```
