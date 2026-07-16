"""Graana.com scraper — placeholder for a future milestone.

Per PLAN.md, Graana is a "future" source, not part of the current
milestone. This stub exists so the `SourceName.GRAANA` enum value has a
corresponding module and the directory structure is ready, without
pretending a real implementation exists yet.
"""

from app.models.enums import SourceName
from scrapers.base.base_scraper import BaseScraper


class GraanaScraper(BaseScraper):
    """Not yet implemented — reserved for a future milestone."""

    source_name = SourceName.GRAANA

    @property
    def base_url(self) -> str:
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")

    def initial_cursor(self) -> str:
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")

    def fetch_listing_page(self, cursor: str) -> str:
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")

    def extract_listing_refs(self, page_html: str) -> list:
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")

    def parse_listing(self, detail_html: str, ref):
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")

    def get_next_cursor(self, current_cursor: str, page_html: str) -> str | None:
        raise NotImplementedError("Graana scraper is planned but not yet implemented.")
