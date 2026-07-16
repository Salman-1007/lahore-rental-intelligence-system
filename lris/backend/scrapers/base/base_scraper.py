"""Abstract base scraper.

Implements everything that must be identical across every source
(pagination loop, retry-with-backoff, rate limiting, resume-after-
interruption, scrape logging) as a template method. Concrete scrapers
(`OLXScraper`, `ZameenScraper`) only implement the four site-specific hook
methods — everything else, including how a run is resumed after a crash,
is handled here exactly once. See RULES.md §4.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.db.session import session_scope
from app.models.enums import ScrapeStatus, SourceName
from app.models.scrape_log import ScrapeLog
from app.models.source import Source
from scrapers.base.dto import RawListing
from scrapers.base.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ListingRef(BaseModel):
    """A lightweight reference to a listing found on a listing page.

    Concrete scrapers extract these from a listing/search results page;
    `BaseScraper` then fetches each one's detail page and hands it to
    `parse_listing`.
    """

    url: str
    source_listing_id: str


@dataclass
class ScrapeRunResult:
    """Summary of a completed (or failed) scrape run."""

    status: ScrapeStatus
    pages_crawled: int
    listings_found: int
    listings_new: int
    error_message: str | None = None


class BaseScraper(ABC):
    """Template-method base class for all site scrapers.

    Attributes:
        source_name: Which `SourceName` this scraper crawls.
        on_listing: Callback invoked with every successfully parsed
            `RawListing` — wired to the ingestion service in production,
            and to a simple list-appender in tests, so this class never
            needs to know about the DB or the pipeline directly.
    """

    source_name: SourceName

    def __init__(self, on_listing: "callable[[RawListing], bool]") -> None:
        """
        Args:
            on_listing: Called once per parsed listing. Must return True if
                the listing was newly stored, False if it was a duplicate
                seen before (used to track `listings_new` in the log).
        """
        settings = get_settings()
        self.on_listing = on_listing
        self.rate_limiter = RateLimiter(
            settings.scraper_min_delay_seconds, settings.scraper_max_delay_seconds
        )
        self.max_retries = settings.scraper_max_retries
        self.timeout = settings.scraper_request_timeout_seconds
        self.http_client = httpx.Client(
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 (LRIS research crawler)"},
            follow_redirects=True,
        )

    # ---- Hook methods every concrete scraper must implement ----

    @abstractmethod
    def initial_cursor(self) -> str:
        """Return the cursor value (e.g. page 1 URL) a fresh run starts at."""

    @abstractmethod
    def fetch_listing_page(self, cursor: str) -> str:
        """Fetch the raw HTML of a listing/search-results page at `cursor`."""

    @abstractmethod
    def extract_listing_refs(self, page_html: str) -> list[ListingRef]:
        """Extract `ListingRef`s (detail page URL + source ID) from a page."""

    @abstractmethod
    def parse_listing(self, detail_html: str, ref: ListingRef) -> RawListing | None:
        """Parse a single detail page into a `RawListing`, or None if unparsable."""

    @abstractmethod
    def get_next_cursor(self, current_cursor: str, page_html: str) -> str | None:
        """Return the next page's cursor, or None if this was the last page."""

    # ---- Shared template-method logic (do not override) ----

    def _fetch_with_retry(self, url: str) -> str:
        """Fetch a URL with exponential backoff on transient failures."""

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
            reraise=True,
        )
        def _do_fetch() -> str:
            response = self.http_client.get(url)
            response.raise_for_status()
            return response.text

        return _do_fetch()

    def run(self, resume: bool = True) -> ScrapeRunResult:
        """Crawl every available page until no new listings remain.

        Args:
            resume: If True, continue from the last incomplete run's
                cursor (per `RULES.md` §4). If False, always start fresh
                from `initial_cursor()`.

        Returns:
            A summary of what this run accomplished.
        """
        with session_scope() as session:
            source = self._get_or_create_source(session)
            log = self._start_log(session, source, resume)
            cursor = log.resume_cursor if (resume and log.resume_cursor) else self.initial_cursor()
            log_id = log.id

        pages_crawled = 0
        listings_found = 0
        listings_new = 0
        previous_page_ids: set[str] | None = None

        try:
            while cursor is not None:
                self.rate_limiter.wait()
                page_html = self._fetch_with_retry(self._absolute_url(cursor))
                refs = self.extract_listing_refs(page_html)

                if not refs:
                    logger.info("No listing refs found at cursor=%s; stopping.", cursor)
                    break

                current_page_ids = {ref.source_listing_id for ref in refs}
                if previous_page_ids is not None and current_page_ids == previous_page_ids:
                    logger.info(
                        "Pagination did not advance at cursor=%s (same %d listings as "
                        "the previous page); stopping instead of looping.",
                        cursor, len(current_page_ids),
                    )
                    break
                previous_page_ids = current_page_ids

                for ref in refs:
                    self.rate_limiter.wait()
                    try:
                        detail_html = self._fetch_with_retry(self._absolute_url(ref.url))
                        raw_listing = self.parse_listing(detail_html, ref)
                    except Exception:
                        logger.exception("Failed to fetch/parse listing %s", ref.url)
                        continue

                    if raw_listing is None:
                        continue

                    listings_found += 1
                    is_new = self.on_listing(raw_listing)
                    if is_new:
                        listings_new += 1

                pages_crawled += 1
                next_cursor = self.get_next_cursor(cursor, page_html)

                with session_scope() as session:
                    self._update_log(
                        session, log_id, next_cursor, pages_crawled, listings_found, listings_new
                    )

                cursor = next_cursor

            with session_scope() as session:
                self._finish_log(session, log_id, ScrapeStatus.COMPLETED)

            return ScrapeRunResult(
                ScrapeStatus.COMPLETED, pages_crawled, listings_found, listings_new
            )

        except Exception as exc:
            logger.exception("Scrape run failed for source=%s", self.source_name)
            with session_scope() as session:
                self._finish_log(session, log_id, ScrapeStatus.FAILED, error_message=str(exc))
            return ScrapeRunResult(
                ScrapeStatus.FAILED, pages_crawled, listings_found, listings_new, str(exc)
            )

    def _absolute_url(self, cursor_or_path: str) -> str:
        """Resolve a possibly-relative cursor/path against the scraper's base URL."""
        if cursor_or_path.startswith("http"):
            return cursor_or_path
        return httpx.URL(self.base_url).join(cursor_or_path).human_repr()

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Root URL of the source site, used to resolve relative links."""

    def _get_or_create_source(self, session) -> Source:
        source = session.query(Source).filter(Source.name == self.source_name).one_or_none()
        if source is None:
            source = Source(
                name=self.source_name,
                display_name=self.source_name.value.title(),
                base_url=self.base_url,
            )
            session.add(source)
            session.flush()
        return source

    def _start_log(self, session, source: Source, resume: bool) -> ScrapeLog:
        previous = None
        if resume:
            previous = (
                session.query(ScrapeLog)
                .filter(
                    ScrapeLog.source_id == source.id,
                    ScrapeLog.status.in_([ScrapeStatus.INTERRUPTED, ScrapeStatus.FAILED]),
                )
                .order_by(ScrapeLog.started_at.desc())
                .first()
            )
        log = ScrapeLog(
            source_id=source.id,
            status=ScrapeStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            resume_cursor=previous.resume_cursor if previous else None,
        )
        session.add(log)
        session.flush()
        return log

    def _update_log(
        self, session, log_id: int, cursor: str | None, pages: int, found: int, new: int
    ) -> None:
        log = session.get(ScrapeLog, log_id)
        log.resume_cursor = cursor
        log.pages_crawled = pages
        log.listings_found = found
        log.listings_new = new

    def _finish_log(
        self, session, log_id: int, status: ScrapeStatus, error_message: str | None = None
    ) -> None:
        log = session.get(ScrapeLog, log_id)
        log.status = status
        log.finished_at = datetime.now(timezone.utc)
        log.error_message = error_message
