# PLAN.md — Milestone Roadmap

LRIS is built in ordered milestones. Each milestone must be working,
tested, and committed before the next begins. Do not parallelize across
milestones — the pipeline stages depend on each other's contracts.

## M0 — Foundation (this milestone)
- Repository scaffold, planning docs, coding rules, architecture doc.
- Base tooling: `requirements.txt`, `.gitignore`, logging config,
  Pydantic settings, pytest setup.
- **Status: in progress.**

## M1 — Database Layer
- SQLAlchemy models for all core tables (Listings, PropertyDetails,
  Dimensions, Locations, PriceHistory, Sources, Duplicates, ScrapeLog).
- Alembic migrations (initial schema).
- Repository layer with typed methods per aggregate.
- Unit + integration tests against SQLite.
- **Status: complete.**

## M2 — Scraper Framework + OLX
- Abstract `BaseScraper` (pagination, retry, rate limiting, resume,
  dedup-on-insert).
- `RawListing` DTO.
- OLX spider implementation, real crawl against Lahore rental category.
- ScrapeLog persistence for resumability.
- **Status: complete (framework + OLX spider code; live crawling must be
  run on a machine with network access to olx.com.pk — see RUNBOOK.md).**

## M3 — Zameen Scraper
- Zameen spider implementing the same `BaseScraper` contract.
- Verify both sources output identical `RawListing` shape.
- **Status: complete.**

## M4 — Parsing & Cleaning Pipeline
- `Parser`: RawListing -> ParsedListing.
- `Cleaner`: unit parsing (marla/kanal/sqft), attribute extraction from
  free-text descriptions (bedrooms, bathrooms, parking, furnished,
  corner, park_facing, servant_quarter, independent_entrance,
  newly_built).
- Cleaner test suite covering edge cases in real description text.
- **Status: complete.**

## M5 — Normalization & Location Engine
- Canonical enums for property_type, portion_type, currency.
- Lahore location hierarchy (City -> Town -> Phase -> Block -> Street)
  with alias generation and fuzzy matching.
- Autocomplete-ready location search function.
- **Status: complete.**

## M6 — Deduplication
- Cross-source duplicate detection (title/description/price/location/
  size/bedrooms/bathrooms similarity scoring).
- Merge logic preserving source history in `duplicates` + `price_history`.
- **Status: complete.**

## M7 — Dataset Versioning & Feature Engineering
- Dataset builder: raw -> clean -> processed -> training/validation,
  timestamped, immutable.
- Feature engineering module: price_per_marla, size_marla,
  location_encoding, one-hots/target-encodings, boolean features,
  distance features if coordinates available.
- **Status: complete (distance features deferred — no listings have
  coordinates yet; add once a source provides lat/lng).**

## M8 — EDA
- Automated report generator: missing values, outliers, price
  distributions, location statistics, feature correlations, summary
  stats. Output as a static HTML/markdown report, not a runtime
  dependency of the API.
- **Status: complete.**

## M9 — Model Training
- CatBoost training pipeline: cross-validation, hyperparameter search,
  early stopping, model persistence with dataset-version linkage.
- Evaluation report: MAE, RMSE, R², MAPE, saved alongside the model
  artifact.
- **Status: complete — run on a machine with real scraped data (see
  RUNBOOK.md); verified end-to-end against synthetic fixture data here.**

## M10 — FastAPI Backend
- Endpoints: `/search`, `/predict`, `/autocomplete`, `/listings`,
  `/stats`, `/trends`, `/docs` (auto-generated).
- Prediction endpoint returns estimate, confidence, min/max range,
  similar listings.
- **Status: complete.**

## M11 — React Frontend
- Search UI with filters (property type, portion, size, bedrooms,
  bathrooms, location with live autocomplete).
- Prediction page: estimated rent, confidence, range, market trend,
  similar listings.
- Modern, professional visual design (see `frontend-design` conventions
  once that milestone starts).
- **Status: complete — "Land Registry" design direction (ink/brass/
  emerald, Fraunces + Inter + IBM Plex Mono). Build verified with
  `npm run build`.**

## M12 — Hardening
- Full test suite pass (unit/integration/parser/cleaner/model/API).
- Performance pass: session reuse, batch inserts, caching where useful.
- Final documentation pass across all four planning docs.

---

**Current milestone: M12 — Hardening.** The full pipeline (scrapers,
cleaning/normalization/dedup, dataset versioning, model training, API,
frontend) is built and verified end-to-end against synthetic data. What
remains is running it against real scraped data on a machine with network
access — see `RUNBOOK.md` — and then the usual hardening pass (broader
test coverage, performance tuning, Postgres deployment).
