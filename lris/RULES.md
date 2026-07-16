# RULES.md — Engineering Rules for LRIS

These rules are non-negotiable defaults. Deviating from any of them
requires a documented reason in the PR/commit description.

## 1. Before making changes

Read, in this order: `PLAN.md`, `TASKS.md`, `RULES.md`, `ARCHITECTURE.md`.
If a change contradicts `ARCHITECTURE.md`, update the architecture doc in
the same commit — the doc and the code must never drift apart.

## 2. Code organization

- One file, one responsibility. If a file is doing two jobs, split it.
- Never duplicate logic. If the same parsing/cleaning/validation logic is
  needed in two places, extract it into a shared utility and import it.
- Site-specific scraping/parsing logic lives ONLY inside
  `scrapers/<site>/`. Nothing outside that folder may know that "OLX" or
  "Zameen" exist.
- No SQL, no `Session` objects, outside `app/repositories/`. Services call
  repositories; repositories call SQLAlchemy.
- Public function/class signatures, once used by another module, are
  stable. Breaking changes require updating every call site in the same
  commit, not a "TODO: fix callers later."

## 3. Python standards

- Full type hints on every function signature (params + return type).
  `Any` is a last resort, not a default.
- Every public function, class, and module has a docstring (Google style):
  short summary, `Args:`, `Returns:`, `Raises:` where relevant.
- Use `logging` (never `print`) for anything beyond a one-off debug script.
  Each module gets its own named logger: `logger = logging.getLogger(__name__)`.
- Configuration comes from `app/core/config.py` (Pydantic `BaseSettings`)
  or `backend/config/*.yaml` — never hardcoded constants scattered across
  files.
- Dependency injection: services/repositories receive their dependencies
  (DB session, HTTP client, settings) through constructor parameters or
  FastAPI's `Depends`, never instantiated ad-hoc inside a function body.
- Repository pattern strictly enforced: one repository class per
  aggregate root (`ListingRepository`, `LocationRepository`, etc.), each
  exposing intention-revealing methods (`get_by_id`, `find_by_location`,
  `upsert_price_observation`) — never a generic `execute_query(sql)`.

## 4. Scrapers

- Every scraper must: paginate until no new listings are found, persist a
  resume cursor (`scrape_log`), retry transient failures with backoff, and
  rate-limit requests.
- Every scraper outputs the same `RawListing` DTO regardless of source.
- Never fabricate or hardcode sample listings. If a site is unreachable,
  the scraper logs and fails loudly — it does not fall back to fake data.
- Deduplicate at the source level (don't re-insert a listing already
  captured in this run) in addition to the cross-source dedup stage later
  in the pipeline.

## 5. Data & datasets

- Never train directly on raw scraped data. Data must pass through
  raw -> clean -> processed -> training/validation, with each stage
  persisted to `data/<stage>/`.
- Every dataset version is timestamped and immutable once written. Never
  overwrite a previous dataset version.
- Every trained model artifact records the exact dataset version (path +
  hash) used to produce it.

## 6. Testing

- New logic ships with tests in the same commit: unit tests for pure
  functions (parser/cleaner/normalizer), integration tests for
  repository + DB interactions, API tests for endpoints, model tests for
  training/evaluation pipeline correctness (not model accuracy — that's
  tracked via the evaluation report, not assertions).
- Tests never hit real external websites. Scraper tests run against
  small, clearly-labeled fixture HTML/JSON saved under
  `tests/fixtures/`.

## 7. Git workflow

- Complete one milestone (see `TASKS.md`) → verify the project builds →
  run the full test suite → commit → move to the next milestone.
- Commit messages: imperative mood, scoped prefix, no fluff.
  Example: `feat(scrapers): add OLX spider with pagination and resume support`
  Example: `fix(cleaner): correct marla/kanal unit conversion rounding`
- Never commit secrets, `.env` files, or raw scraped data dumps.

## 8. The standing question

Before merging any non-trivial change, ask:
**"Would a senior software engineer approve this architecture?"**
If the honest answer is no, revise before moving on — do not defer
architectural debt "for later."
