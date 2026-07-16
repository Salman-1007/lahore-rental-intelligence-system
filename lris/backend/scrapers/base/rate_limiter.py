"""Rate limiting helper shared by every scraper.

A tiny module on purpose — its only job is "wait a randomized, configured
amount of time between requests," so every scraper is polite to the sites
it crawls without duplicating sleep logic per-site.
"""

import logging
import random
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sleeps a randomized interval between `min_delay` and `max_delay`."""

    def __init__(self, min_delay_seconds: float, max_delay_seconds: float) -> None:
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds

    def wait(self) -> None:
        """Block for a randomized delay before the next request."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug("Rate limiting: sleeping %.2fs", delay)
        time.sleep(delay)
