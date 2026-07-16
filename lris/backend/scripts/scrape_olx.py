"""CLI entrypoint: run the OLX scraper and ingest results into the database.

Usage (from backend/):
    python -m scripts.scrape_olx
    python -m scripts.scrape_olx --fresh   # ignore any resume cursor
"""

import argparse
import logging

from app.core.logging_config import configure_logging
from app.db.session import session_scope
from app.services.ingestion_service import ingest_raw_listing
from scrapers.olx.scraper import OLXScraper

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OLX scraper.")
    parser.add_argument(
        "--fresh", action="store_true", help="Ignore resume cursor, start from page 1."
    )
    args = parser.parse_args()

    def on_listing(raw_listing) -> bool:
        with session_scope() as session:
            return ingest_raw_listing(raw_listing, session)

    scraper = OLXScraper(on_listing=on_listing)
    result = scraper.run(resume=not args.fresh)

    logger.info(
        "OLX run finished: status=%s pages=%d found=%d new=%d",
        result.status.value,
        result.pages_crawled,
        result.listings_found,
        result.listings_new,
    )


if __name__ == "__main__":
    main()
