"""OLX Pakistan scraper for Lahore rental listings.

Verified against a live fetch of the real page (2026-07-16):
- City code is `lahore_g4060673` (not a guessed value).
- Category slug is `property-for-rent_c3` (covers houses, portions,
  flats, and rooms in one feed; narrower category-specific slugs also
  exist — e.g. `houses_c1719`, `portions-floors_c39` — if you want to
  scrape one property type at a time instead).
- Item URLs look like `/item/<slug>-iid-<numeric-id>`, confirmed from
  real hrefs on the page — hence the `_ITEM_ID_PATTERN` below.

KNOWN LIMITATION — pagination: this page loads its initial batch of
listings server-rendered, but appending `?page=2` returned the exact
same content, meaning further listings load via client-side JS
(infinite scroll), not a URL you can page through with a plain HTTP
GET. `get_next_cursor` below makes a best-effort attempt at `?page=N`
anyway; `BaseScraper` detects if a "next page" returns the same
listings as the last one and stops cleanly rather than looping forever
on duplicate content (see `base_scraper.py`). In practice this means a
single run captures whatever OLX server-renders for that category
(historically 20-40 fresh listings) — re-running periodically still
accumulates real data over time, since this category turns over
listings every few minutes. If you want deeper pagination, open the
page in a browser, scroll down, and inspect the Network tab for the
XHR request the page fires — that's the real paginated endpoint, and
`fetch_listing_page`/`get_next_cursor` below are exactly where you'd
wire it in once you've found it.
"""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.models.enums import SourceName
from scrapers.base.base_scraper import BaseScraper, ListingRef
from scrapers.base.dto import RawListing

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.olx.com.pk"
_LAHORE_RENTAL_PATH = "/lahore_g4060673/property-for-rent_c3"

_ITEM_HREF_PATTERN = re.compile(r"^/item/[^\"'\s]*-iid-(\d+)$")

_SELECTORS = {
    "title": "h1",
    "price": "[data-aut-id='itemPrice'], [aria-label='Price']",
    "description": "[data-aut-id='itemDescriptionText'], [aria-label='Description']",
    "location": "[data-aut-id='item-location'], [aria-label='Location']",
}


class OLXScraper(BaseScraper):
    """Scraper for OLX Pakistan's Lahore rental listings."""

    source_name = SourceName.OLX

    @property
    def base_url(self) -> str:
        return _BASE_URL

    def initial_cursor(self) -> str:
        return urljoin(_BASE_URL, _LAHORE_RENTAL_PATH)

    def fetch_listing_page(self, cursor: str) -> str:
        return self._fetch_with_retry(cursor)

    def extract_listing_refs(self, page_html: str) -> list[ListingRef]:
        """Find every `/item/...-iid-<id>` link on the page.

        Matching on the href pattern itself (confirmed real) rather than
        a wrapping div's class/data-attribute (never verified against
        live markup) is what makes this resilient to markup changes that
        don't touch the URL structure.
        """
        soup = BeautifulSoup(page_html, "lxml")
        seen_ids: set[str] = set()
        refs: list[ListingRef] = []

        for link in soup.find_all("a", href=True):
            match = _ITEM_HREF_PATTERN.match(link["href"])
            if not match:
                continue
            listing_id = match.group(1)
            if listing_id in seen_ids:
                continue
            seen_ids.add(listing_id)
            refs.append(
                ListingRef(url=urljoin(_BASE_URL, link["href"]), source_listing_id=listing_id)
            )
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

        return RawListing(
            source=self.source_name,
            source_listing_id=ref.source_listing_id,
            source_url=ref.url,
            title=title_el.get_text(strip=True),
            description=desc_el.get_text(strip=True) if desc_el else None,
            price_raw=price_el.get_text(strip=True),
            location_raw=location_el.get_text(strip=True) if location_el else "",
            size_raw=self._extract_size_hint(desc_el.get_text(" ", strip=True) if desc_el else ""),
        )

    def get_next_cursor(self, current_cursor: str, page_html: str) -> str | None:
        """Best-effort `?page=N` guess — see the module docstring's caveat.

        `BaseScraper.run` will detect if this doesn't actually advance
        (same listings as the previous page) and stop instead of looping.
        """
        current_page = 1
        match = re.search(r"[?&]page=(\d+)", current_cursor)
        if match:
            current_page = int(match.group(1))

        base = current_cursor.split("?")[0]
        return f"{base}?page={current_page + 1}"

    @staticmethod
    def _extract_size_hint(text: str) -> str | None:
        """Grab a `<number> <marla|kanal|sq ft>` fragment from free text.

        OLX often puts size only in the free-text title/description rather
        than a dedicated field, so this is a light heuristic, not a
        guarantee — the cleaner stage does the authoritative parsing.
        """
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(marla|kanal|sq\.?\s*ft|square\s*feet|sq\.?\s*yd)",
            text,
            re.IGNORECASE,
        )
        return match.group(0) if match else None
