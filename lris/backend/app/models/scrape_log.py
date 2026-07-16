"""Scrape run history — what makes resumable, auditable scraping possible.

Every `BaseScraper` run (see `scrapers/base/`) writes one row here at
start, updates it as pages are crawled, and finalizes it on completion or
failure. `resume_cursor` is what lets a scraper pick back up after an
interruption instead of re-crawling from page 1.
"""

from datetime import datetime

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ScrapeStatus


class ScrapeLog(Base, TimestampMixin):
    """A single scrape run against one source.

    Attributes:
        id: Primary key.
        source_id: FK to the `Source` this run scraped.
        status: Current status of the run.
        started_at: When the run began.
        finished_at: When the run ended (null while still running).
        pages_crawled: Number of listing pages successfully crawled so far.
        listings_found: Total listings encountered (including duplicates
            within the run).
        listings_new: Listings that were new inserts (not already present
            for this source).
        resume_cursor: Opaque cursor (e.g. a page number or last-seen
            listing ID) a new run reads to continue after an interruption.
        error_message: Populated when `status` is `FAILED`.
    """

    __tablename__ = "scrape_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)

    status: Mapped[ScrapeStatus] = mapped_column(
        SAEnum(ScrapeStatus), default=ScrapeStatus.RUNNING, nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    pages_crawled: Mapped[int] = mapped_column(default=0, nullable=False)
    listings_found: Mapped[int] = mapped_column(default=0, nullable=False)
    listings_new: Mapped[int] = mapped_column(default=0, nullable=False)

    resume_cursor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["Source"] = relationship(back_populates="scrape_logs")

    def __repr__(self) -> str:
        return f"<ScrapeLog id={self.id} source_id={self.source_id} status={self.status.value}>"
