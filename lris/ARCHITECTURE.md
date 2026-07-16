# ARCHITECTURE.md — Lahore Rental Intelligence System (LRIS)

## 1. Purpose

LRIS is a data platform that scrapes real rental listings from Pakistani real
estate portals (OLX, Zameen, later Graana), normalizes them into a clean
relational schema, engineers ML-ready features, trains a rent-estimation
model that generalizes to unseen property combinations, and exposes both
the data and the model through a FastAPI backend consumed by a React
frontend.

The system is organized as a **pipeline of independent, swappable stages**.
Each stage has one responsibility, a stable input/output contract, and no
knowledge of any other stage's internals.

```
Real Websites
     │
     ▼
 Scrapers            (site-specific crawl + raw HTML/JSON capture)
     │
     ▼
 Parser              (site-specific HTML/JSON -> RawListing DTO)
     │
     ▼
 Cleaner             (text normalization, unit parsing, attribute extraction)
     │
     ▼
 Normalizer          (canonical enums, location hierarchy resolution)
     │
     ▼
 Database            (SQLAlchemy ORM, repository pattern)
     │
     ▼
 Deduplication       (cross-source entity resolution)
     │
     ▼
 Feature Engineering (derived numeric/categorical features)
     │
     ▼
 Dataset Versioning  (raw -> clean -> processed -> training/validation)
     │
     ▼
 EDA                 (automated reporting, not a runtime dependency)
     │
     ▼
 Model Training       (CatBoost, CV, hyperparameter search)
     │
     ▼
 Evaluation           (MAE, RMSE, R², MAPE, persisted report)
     │
     ▼
 FastAPI              (serves predictions + search + stats)
     │
     ▼
 React Frontend       (search, autocomplete, prediction UI)
```

## 2. Guiding Principles

1. **Single Responsibility** — one file, one job. A parser never cleans. A
   cleaner never touches the database. A repository never contains scraping
   logic.
2. **Stable contracts, swappable internals** — every stage communicates
   through a well-defined DTO (`RawListing`, `CleanedListing`,
   `NormalizedListing`, `FeatureVector`). Internals can change without
   breaking downstream stages.
3. **No site-specific logic outside `scrapers/<site>/`** — OLX quirks stay
   in `scrapers/olx`, Zameen quirks stay in `scrapers/zameen`. Everything
   downstream operates on the same normalized shape regardless of source.
4. **No SQL outside the repository layer** — services and pipeline stages
   never construct raw queries or touch `Session` objects directly.
5. **Data lineage over convenience** — a scraped record's raw form is never
   discarded; datasets are versioned and timestamped; every trained model
   records which dataset version produced it.
6. **Real data only** — scrapers hit real endpoints. No fixtures pretending
   to be scraped data. Tests use small, explicitly-fake sample HTML fixtures
   that are clearly labeled as test fixtures, never presented as real
   listings.

## 3. Module Map

```
backend/
├── app/                      # FastAPI application
│   ├── main.py                # app factory, startup/shutdown hooks
│   ├── api/v1/                 # versioned route modules (thin controllers)
│   ├── core/                   # settings, logging, security, DI container
│   ├── db/                     # engine/session management, base class
│   ├── models/                 # SQLAlchemy ORM models (schema only)
│   ├── repositories/           # data access layer (one repo per aggregate)
│   ├── schemas/                # Pydantic request/response models
│   └── services/                # orchestration/business logic
│
├── scrapers/
│   ├── base/                   # abstract Scraper, RateLimiter, RetryPolicy,
│   │                            #   Checkpoint/resume support, RawListing DTO
│   ├── olx/                    # OLX-specific spider + raw parser
│   ├── zameen/                 # Zameen-specific spider + raw parser
│   └── graana/                 # placeholder for future source
│
├── pipeline/
│   ├── parser/                  # RawListing -> ParsedListing (shared shape)
│   ├── cleaner/                  # text/unit normalization, attribute extraction
│   ├── normalizer/                # canonical enums, currency, property types
│   ├── dedup/                     # cross-source duplicate detection/merge
│   └── location_engine/            # Lahore hierarchy, aliasing, fuzzy search
│
├── ml/
│   ├── features/                # feature engineering transformers
│   ├── datasets/                 # dataset builder + versioning (raw/clean/processed/training/validation)
│   ├── training/                 # CatBoost training + hyperparameter search
│   ├── evaluation/                # metrics + evaluation report generation
│   ├── models_registry/           # persisted model artifacts + metadata
│   └── eda/                       # automated EDA report generation
│
├── tests/
├── config/                        # YAML/env-based configuration files
└── alembic/                       # DB migrations

frontend/                            # React app (Milestone: Frontend)
data/                                 # versioned dataset storage (gitignored, structure tracked)
```

## 4. Data Contracts (DTOs)

Defined with Pydantic so validation is enforced at every stage boundary.

- `RawListing` — exactly what a scraper extracted, source-tagged, minimal
  transformation. One per (source, source_listing_id).
- `ParsedListing` — RawListing normalized into a shared field shape
  (still may contain free text / unnormalized units).
- `CleanedListing` — units parsed (marla/kanal/sqft -> canonical),
  booleans extracted from description (furnished, corner, park_facing,
  servant_quarter, independent_entrance, newly_built), bedrooms/bathrooms/
  parking coerced to int.
- `NormalizedListing` — canonical enums applied (PropertyType, PortionType),
  location resolved against the Location hierarchy, currency normalized to
  PKR.
- `FeatureVector` — the ML-ready row: numeric + encoded categorical +
  derived features (price_per_marla, location_encoding, etc).

## 5. Database Schema (high level)

| Table          | Responsibility                                              |
|----------------|---------------------------------------------------------------|
| `sources`      | Registry of scrape sources (OLX, Zameen, Graana) + config     |
| `listings`     | Canonical listing record (one row per deduplicated property)  |
| `property_details` | Structured attributes (bedrooms, bathrooms, furnished, etc) |
| `dimensions`   | Size records (value + unit + canonical marla equivalent)      |
| `locations`    | Lahore hierarchy: city/town/phase/block/street + aliases       |
| `price_history`| Time-series of price observations per listing                 |
| `duplicates`   | Cross-source duplicate links + merge metadata                  |
| `scrape_log`   | Run history: start/end, pages crawled, errors, resume cursor   |

All relationships use explicit foreign keys, indexes on lookup columns
(`location_id`, `source_id`, `scraped_at`), and constraints (e.g. price > 0,
size > 0) enforced at the ORM level.

## 6. Prediction Design

The model must estimate rent for **unseen combinations** (e.g. a portion
type / size combination never seen together in training). This rules out
any lookup-table or nearest-neighbor-only approach as the primary method.

Approach:
- CatBoost gradient boosting over engineered features (handles categorical
  features natively, robust with moderate data volume).
- Feature set includes generalizable signals (price_per_marla trends by
  location, property_type, portion_type) rather than only raw identifiers,
  so the model can interpolate/extrapolate across combinations.
- Prediction response includes an estimate range (from quantile models or
  residual-based confidence intervals — decided at model-training milestone)
  and a set of similar real listings for the user to sanity-check against.

## 7. Configuration & Environments

- `backend/config/` holds environment-specific YAML (dev/prod) merged with
  `.env` secrets via Pydantic `BaseSettings`.
- Development DB: SQLite (`data/dev.db`).
- Production DB: PostgreSQL (connection string via env var).
- Alembic manages all schema migrations; no `create_all()` in production
  code paths.

## 8. Why these technology choices

- **SQLAlchemy + Alembic**: mature ORM + migrations, works identically
  against SQLite (dev) and PostgreSQL (prod) with minimal dialect friction.
- **FastAPI**: async-capable, Pydantic-native (matches our DTO strategy),
  automatic OpenAPI docs satisfies the `/docs` requirement for free.
- **CatBoost**: best-in-class native categorical handling, which matters
  heavily here (property_type, portion_type, location are all categorical
  and high-cardinality for location).
- **React**: matches the user's existing MERN experience; fastest path to
  a polished, maintainable frontend.

This document is updated whenever an architectural decision changes. It is
read before any structural change to the repository.
