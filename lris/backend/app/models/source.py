"""Registry of scrape sources (OLX, Zameen, Graana, ...)."""

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import SourceName


class Source(Base, TimestampMixin):
    """A website LRIS scrapes listings from.

    Attributes:
        id: Primary key.
        name: Canonical source identifier (`SourceName`).
        display_name: Human-readable name for UI/reporting.
        base_url: Root URL of the source site.
        is_active: Whether scrapers should currently crawl this source.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[SourceName] = mapped_column(SAEnum(SourceName), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    listings: Mapped[list["Listing"]] = relationship(back_populates="source")
    scrape_logs: Mapped[list["ScrapeLog"]] = relationship(back_populates="source")

    def __repr__(self) -> str:
        return f"<Source id={self.id} name={self.name.value}>"
