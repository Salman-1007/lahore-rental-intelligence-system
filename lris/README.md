# Lahore Rental Intelligence System (LRIS)

A production-grade pipeline that scrapes real Lahore rental listings from
OLX and Zameen (Graana planned), normalizes and deduplicates them into a
relational database, engineers ML features, trains a CatBoost model that
estimates rent for unseen property combinations, and serves everything
through a FastAPI backend + React frontend.

Read these before contributing, in order:

1. [`PLAN.md`](./PLAN.md) — milestone roadmap
2. [`TASKS.md`](./TASKS.md) — granular task checklist for the active milestone
3. [`RULES.md`](./RULES.md) — engineering conventions (non-negotiable)
4. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — system design and data contracts
5. [`RUNBOOK.md`](./RUNBOOK.md) — **exact commands** to scrape real data,
   train the model, and run the full stack
6. [`DEPLOYMENT.md`](./DEPLOYMENT.md) — deploying to free-tier hosting
   (Vercel for the frontend, Render + Neon for the backend/database)

## Current status

**M0–M11 complete.** The full pipeline — scrapers, cleaning/normalization/
dedup, database, dataset versioning, EDA, CatBoost training + evaluation,
FastAPI backend, and the React frontend — is built and verified end-to-end
against synthetic fixture data (35/35 backend tests passing; frontend
builds cleanly). What's left is running it against real data, which needs
to happen on a machine with real network access — see `RUNBOOK.md`.

## Local setup

See `RUNBOOK.md` for the full walkthrough (scraping, training, running
everything together). Quick version:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
alembic upgrade head
uvicorn app.main:app --reload
# -> http://127.0.0.1:8000/docs

# separate terminal
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

Run tests:

```bash
cd backend
pytest
```

## Project layout

```
backend/
  app/          FastAPI application (routes, services, repositories, ORM models)
  scrapers/     Site-specific scrapers (OLX, Zameen, Graana) behind a shared base class
  pipeline/     Parsing, cleaning, normalization, dedup, location engine
  ml/           Feature engineering, dataset versioning, training, evaluation, EDA
  scripts/      CLI entrypoints: scrape_olx, scrape_zameen, build_dataset
  tests/        Unit, integration, parser, cleaner, model, and API tests
  config/       Environment-specific configuration
  alembic/      Database migrations
frontend/       React app (Vite) — Search, Estimate, Insights, Listing detail
data/           Versioned datasets (raw/clean/processed/training/validation) — gitignored contents
```

See `ARCHITECTURE.md` for the full data flow and module responsibilities,
and `RUNBOOK.md` for exact commands to go from zero to a trained model and
a running app.
