"""Zameen.com scraper for Lahore rental listings.

Same caveat as the OLX scraper: `_SELECTORS` is a best-effort starting
point, not verified against a live page (this environment cannot reach
zameen.com). Expect to adjust it once you point this at the real site.
"""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models.enums import SourceName
from scrapers.base.base_scraper import BaseScraper, ListingRef
from scrapers.base.dto import RawListing

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.zameen.com"
_LAHORE_RENTAL_PATH = "/Rentals/Lahore-1-1.html"

_SELECTORS = {
    "listing_card": "li[aria-label='Listing']",
    "listing_link": "a",
    "next_page": "a[title='Next']",
    "title": "h1",
    "price": "span[aria-label='Price']",
    "description": "div[aria-label='Description']",
    "location": "div[aria-label='Location']",
}


class ZameenScraper(BaseScraper):
    """Scraper for Zameen.com's Lahore rental listings."""

    source_name = SourceName.ZAMEEN

    @property
    def base_url(self) -> str:
        return _BASE_URL

    def initial_cursor(self) -> str:
        return urljoin(_BASE_URL, _LAHORE_RENTAL_PATH)

    def fetch_listing_page(self, cursor: str) -> str:
        return self._fetch_with_retry(cursor)

    def extract_listing_refs(self, page_html: str) -> list[ListingRef]:
        soup = BeautifulSoup(page_html, "lxml")
        refs: list[ListingRef] = []
        for card in soup.select(_SELECTORS["listing_card"]):
            link = card.select_one(_SELECTORS["listing_link"])
            if link is None or not link.get("href"):
                continue
            href = urljoin(_BASE_URL, link["href"])
            listing_id = self._extract_id_from_url(href)
            if listing_id:
                refs.append(ListingRef(url=href, source_listing_id=listing_id))
        return refs

    def parse_listing(self, detail_html: str, ref: ListingRef) -> RawListing | None:
        soup = BeautifulSoup(detail_html, "lxml")

        title_el = soup.select_one(_SELECTORS["title"])
        price_el = soup.select_one(_SELECTORS["price"])
        desc_el = soup.select_one(_SELECTORS["description"])
        location_el = soup.select_one(_SELECTORS["location"])

        if title_el is None or price_el is None:
            logger.warning("Missing required fields for %s; skipping.", ref.url)
            return None

        full_text = " ".join(
            t.get_text(" ", strip=True) for t in (title_el, desc_el) if t is not None
        )

        return RawListing(
            source=self.source_name,
            source_listing_id=ref.source_listing_id,
            source_url=ref.url,
            title=title_el.get_text(strip=True),
            description=desc_el.get_text(strip=True) if desc_el else None,
            price_raw=price_el.get_text(strip=True),
            location_raw=location_el.get_text(strip=True) if location_el else "",
            size_raw=self._extract_size_hint(full_text),
        )

    def get_next_cursor(self, current_cursor: str, page_html: str) -> str | None:
        soup = BeautifulSoup(page_html, "lxml")
        next_link = soup.select_one(_SELECTORS["next_page"])
        if next_link is None or not next_link.get("href"):
            return None
        return urljoin(_BASE_URL, next_link["href"])

    @staticmethod
    def _extract_id_from_url(url: str) -> str | None:
        """Zameen URLs end in `...-<numeric-id>.html`."""
        match = re.search(r"-(\d+)\.html", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_size_hint(text: str) -> str | None:
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(marla|kanal|sq\.?\s*ft|square\s*feet|sq\.?\s*yd)",
            text,
            re.IGNORECASE,
        )
        return match.group(0) if match else None
