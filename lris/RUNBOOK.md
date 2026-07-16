# RUNBOOK.md — Running LRIS End-to-End

This is the single reference for getting real data flowing through the
whole system: scrape -> train -> serve. Run everything from your own
machine (not a sandboxed environment) since scraping needs real network
access to olx.com.pk and zameen.com, and training benefits from your
machine's CPU/RAM.

All backend commands below assume your terminal's working directory is
`backend/` unless stated otherwise. All frontend commands assume `frontend/`.

---

## 0. One-time setup

```bash
# --- Backend ---
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example ../.env           # adjust DATABASE_URL etc. if needed

# Create the database schema
alembic upgrade head

# --- Frontend (separate terminal/tab) ---
cd frontend
npm install
```

---

## 1. Scrape real listings

Selectors in `scrapers/olx/scraper.py` and `scrapers/zameen/scraper.py`
are a best-effort starting point (written without live access to those
sites). **The first time you run these, expect to open browser dev tools,
inspect the real page structure, and adjust the `_SELECTORS` dict at the
top of each scraper file if OLX/Zameen's markup has changed.** This is
normal scraper maintenance, not a bug in the framework around it.

**OLX note (fixed 2026-07-16):** the original OLX category URL was wrong
(bad city code + category slug → 404). It's now verified against a live
fetch of `https://www.olx.com.pk/lahore_g4060673/property-for-rent_c3`.
Item-link extraction also switched from an unverified `data-aut-id`
selector to matching the real `/item/...-iid-<id>` URL pattern directly,
which is more resilient to markup changes. **Known limitation:** this
category page appears to load its first batch server-rendered, but
further listings load via client-side JS (infinite scroll) rather than
a `?page=2`-style URL — appending `?page=2` returned identical content
in testing. `BaseScraper` now detects this (identical listings on
consecutive "pages") and stops cleanly instead of looping. In practice
this means one run captures whatever OLX server-renders for that
category — re-running periodically still accumulates real data over
time, since this category turns over new listings every few minutes. If
you want deeper pagination, open the page in a browser, scroll down, and
check the Network tab for the XHR request the page fires when loading
more results — that's the real paginated endpoint to wire into
`fetch_listing_page`/`get_next_cursor`.

```bash
cd backend
source .venv/bin/activate

# Run each scraper. These crawl every available page and stop only when
# no new listings remain (per RULES.md). Safe to Ctrl+C at any time -
# progress is checkpointed in the scrape_log table and the next run
# resumes from where it left off.
python -m scripts.scrape_olx
python -m scripts.scrape_zameen

# To ignore a previous incomplete run and start over from page 1:
python -m scripts.scrape_olx --fresh
python -m scripts.scrape_zameen --fresh
```

Run these periodically (e.g. daily via cron) to keep growing the dataset.
Re-running is safe - already-seen listings are skipped or price-updated,
never duplicated (see `ingestion_service.py`).

**Check what you've collected:**

```bash
python -c "
from app.db.session import session_scope
from app.models.listing import Listing
with session_scope() as s:
    print('Total listings:', s.query(Listing).count())
    print('Active listings:', s.query(Listing).filter(Listing.is_active.is_(True)).count())
"
```

You'll want at least a few hundred active listings before training
produces a useful model - the more, the better the location encoding and
the more combinations the model has genuinely learned relationships from.

---

## 2. Build a versioned dataset + EDA report

```bash
cd backend
source .venv/bin/activate

python -m scripts.build_dataset
```

This queries every active listing, cleans it, engineers features, and
writes an immutable, timestamped version under `data/raw/`, `data/clean/`,
`data/processed/`, `data/training/`, `data/validation/`. It prints the
**dataset version string** (e.g. `20260716T142233Z`) and the path to an
EDA report (`data/processed/<version>/eda_report.md`) - open that report
to check for missing values, outliers, and price distribution before
training.

If you get a `ValueError` about too few usable listings, scrape more data
first (need at least ~20 clean rows, but realistically want hundreds+).

---

## 3. Train the model

This is the step you run on your own machine, not in any sandboxed
environment - it needs real data and real compute.

```bash
cd backend
source .venv/bin/activate

# Use the dataset version string printed by build_dataset.py
python -m ml.training.train 20260716T142233Z
```

This runs K-fold cross-validated hyperparameter search over CatBoost
depth/learning-rate/L2, fits a final model with early stopping, fits two
additional quantile models (for the confidence range), and writes
everything to `ml/models_registry/<model_version>/`:

- `main_model.cbm`, `lower_model.cbm`, `upper_model.cbm`
- `metadata.json` (which dataset version, params, feature columns)
- `evaluation_report.json` (MAE, RMSE, R², MAPE)

The API automatically picks up the **most recently trained** model - no
config change needed. Check the evaluation report before trusting it:

```bash
cat ml/models_registry/<model_version>/evaluation_report.json
```

Re-run steps 1-3 periodically as you scrape more data, to keep the model
current. Each run produces a new, separately-versioned model; nothing is
overwritten.

---

## 4. Run the full project

Two terminals:

```bash
# Terminal 1 - backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
# -> http://127.0.0.1:8000/docs   (interactive API docs)
# -> http://127.0.0.1:8000/health

# Terminal 2 - frontend
cd frontend
npm run dev
# -> http://localhost:5173
```

Open `http://localhost:5173` - the frontend proxies `/api/*` to the
backend automatically (configured in `frontend/vite.config.js`), so no
extra setup is needed.

- **Search Records** (`/`) - filter and browse scraped listings
- **Estimate Rent** (`/estimate`) - get a prediction; requires a trained
  model (step 3) or you'll see a 503 with a clear message
- **Market Insights** (`/insights`) - aggregate stats + price trend chart

---

## 5. Production build (optional)

```bash
cd frontend
npm run build      # outputs static files to frontend/dist/
npm run preview    # serve the production build locally to sanity-check
```

For a real deployment, switch `DATABASE_URL` in `.env` to a PostgreSQL
connection string (see `ARCHITECTURE.md` §7) and serve `frontend/dist/`
from any static host, pointed at your deployed API's URL.

---

## Quick reference

| Task | Command |
|---|---|
| Create/upgrade DB schema | `alembic upgrade head` |
| Scrape OLX | `python -m scripts.scrape_olx` |
| Scrape Zameen | `python -m scripts.scrape_zameen` |
| Build dataset + EDA | `python -m scripts.build_dataset` |
| Train model | `python -m ml.training.train <dataset_version>` |
| Run backend | `uvicorn app.main:app --reload` |
| Run frontend | `npm run dev` (in `frontend/`) |
| Run backend tests | `pytest` (in `backend/`) |
| Run frontend build | `npm run build` (in `frontend/`) |
