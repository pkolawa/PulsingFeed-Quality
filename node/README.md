# PulsingFeed Quality — Node.js Services

Trzy niezależne serwisy Node.js obsługujące zbieranie artykułów, REST API oraz interfejs webowy.

```
node/
├── api/        REST API          → http://localhost:3001
├── collector/  Kolektor RSS       (cron, brak portu HTTP)
└── web/        Dashboard UI      → http://localhost:3000
```

---

## Wymagania

- **Node.js** ≥ 20
- **npm** ≥ 9
- Działająca baza **PostgreSQL** (schemat z katalogu `../db/`)

---

## Konfiguracja środowiska

Każdy serwis czyta zmienne z pliku `.env` w swoim katalogu.
Utwórz plik `.env` w każdym podkatalogu na podstawie poniższego wzoru.

### `api/.env`

```env
DATABASE_URL=postgresql://user:password@localhost:5432/pulsingfeed
PORT=3001
```

### `collector/.env`

```env
DATABASE_URL=postgresql://user:password@localhost:5432/pulsingfeed
COLLECTOR_CRON=*/15 * * * *
```

> `COLLECTOR_CRON` to wyrażenie cron. Domyślnie: co 15 minut.

### `web/.env`

```env
PORT=3000
API_URL=http://localhost:3001
```

---

## Instalacja i uruchomienie

### Opcja A — wszystkie serwisy naraz (z katalogu `node/`)

```bash
# 1. Zainstaluj zależności we wszystkich serwisach
npm install

# 2. Uruchom wszystkie serwisy (tryb produkcyjny)
npm start

# lub w trybie developerskim (nodemon — auto-restart po zmianie pliku)
npm run dev
```

### Opcja B — serwisy osobno (osobne terminale)

```bash
# Terminal 1 — REST API
cd api
npm install
npm run dev

# Terminal 2 — Kolektor RSS
cd collector
npm install
npm run dev

# Terminal 3 — Dashboard Web
cd web
npm install
npm run dev
```

---

## Kolejność uruchamiania

Serwisy są niezależne, ale zalecana kolejność:

1. **PostgreSQL** — musi działać przed wszystkimi serwisami
2. **api** — kolektor i web nie wymagają go do startu, ale web odpytuje API przy każdym żądaniu
3. **collector** — może startować w dowolnym momencie
4. **web** — wymaga działającego API do wyświetlania danych

---

## Weryfikacja działania

Po uruchomieniu sprawdź:

```bash
# Health check API
curl http://localhost:3001/api/health

# Lista wydawców
curl http://localhost:3001/api/publishers

# Dashboard webowy — otwórz w przeglądarce
open http://localhost:3000
```

---

## Dostępne endpointy API

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `GET` | `/api/health` | Status serwisu |
| `GET` | `/api/publishers` | Lista wydawców z rankingiem |
| `GET` | `/api/publishers/:id` | Szczegóły wydawcy + trend |
| `POST` | `/api/publishers` | Dodaj nowe źródło RSS |
| `DELETE` | `/api/publishers/:id` | Usuń wydawcę |
| `GET` | `/api/articles` | Lista artykułów (filtry: `publisher_id`, `status`, `sort`, `limit`, `offset`) |
| `GET` | `/api/articles/:id` | Pełna analiza artykułu |

---

## Rozwiązywanie problemów

**`Cannot connect to database`**
→ Sprawdź czy PostgreSQL działa i czy `DATABASE_URL` w `.env` jest poprawny.

**Web nie wyświetla danych**
→ Sprawdź czy `api` działa na porcie z `API_URL` w `web/.env`.

**Kolektor nie zbiera artykułów**
→ Sprawdź logi — pierwsze pobranie następuje od razu po starcie, kolejne według harmonogramu `COLLECTOR_CRON`.
