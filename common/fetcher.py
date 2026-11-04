"""
Polite HTTP Fetcher with disk caching, random jitter delays, stealth headers,
and automatic exponential backoff to avoid detection or rate limits.
"""

import os
import time
import json
import random
import hashlib
from pathlib import Path
from typing import Optional, Union
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8,application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


class PoliteFetcher:
    """
    Polite HTTP client that:
    1. Checks local disk cache before making any network requests.
    2. Imposes randomized delays (jitter) between live requests to look like normal browsing.
    3. Retries automatically with exponential backoff if throttled (HTTP 429).
    4. Caches both raw HTML and JSON responses to disk.
    """

    def __init__(
        self,
        cache_dir: str = ".cache",
        cache_ttl_minutes: float = 30.0,
        min_delay: float = 2.0,
        max_delay: float = 4.5,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_minutes = cache_ttl_minutes
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._last_request_time = 0.0

    def _get_cache_path(self, url: str, ext: str = ".json") -> Path:
        """Compute deterministic cache filename from URL."""
        # Use url path basename if readable, plus hash to guarantee uniqueness
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        clean_slug = url.split("?")[0].rstrip("/").split("/")[-1]
        clean_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in clean_slug)
        filename = f"{clean_slug}_{url_hash}{ext}"
        return self.cache_dir / filename

    def _is_cache_fresh(self, cache_path: Path) -> bool:
        """Check if cached file exists and is younger than TTL."""
        if not cache_path.exists():
            return False
        age_minutes = (time.time() - cache_path.stat().st_mtime) / 60.0
        return age_minutes < self.cache_ttl_minutes

    def _throttle(self):
        """Enforce randomized jitter delay since previous live request."""
        elapsed = time.time() - self._last_request_time
        target_delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < target_delay:
            sleep_time = target_delay - elapsed
            time.sleep(sleep_time)

    def fetch(
        self,
        url: str,
        is_json: bool = True,
        force_refresh: bool = False,
        max_retries: int = 3,
    ) -> Union[dict, str]:
        """
        Fetch URL using disk cache first, falling back to polite network request.
        """
        ext = ".json" if is_json else ".html"
        cache_path = self._get_cache_path(url, ext=ext)

        # 1. Cache check
        if not force_refresh and self._is_cache_fresh(cache_path):
            age_min = (time.time() - cache_path.stat().st_mtime) / 60.0
            print(f"  [CACHE HIT] {cache_path.name} ({age_min:.1f} min old)")
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f) if is_json else f.read()

        # 2. Polite live fetch with rate limiting and exponential backoff
        for attempt in range(1, max_retries + 1):
            self._throttle()
            print(f"  [FETCH LIVE] {url} (attempt {attempt}/{max_retries})...")
            
            try:
                resp = self.session.get(url, timeout=25)
                self._last_request_time = time.time()

                if resp.status_code == 429:
                    wait_sec = (2 ** attempt) * 5 + random.uniform(1.0, 3.0)
                    print(f"  [RATE LIMITED 429] Backing off for {wait_sec:.1f}s...")
                    time.sleep(wait_sec)
                    continue

                resp.raise_for_status()

                # Save to cache
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)

                return resp.json() if is_json else resp.text

            except requests.RequestException as e:
                print(f"  [REQUEST ERROR] {e}")
                if attempt == max_retries:
                    # If cached copy exists (even if stale), use as emergency fallback
                    if cache_path.exists():
                        print(f"  [STALE CACHE FALLBACK] Returning older cache due to fetch error.")
                        with open(cache_path, "r", encoding="utf-8") as f:
                            return json.load(f) if is_json else f.read()
                    raise

                wait_sec = (2 ** attempt) * 2 + random.uniform(1.0, 2.0)
                time.sleep(wait_sec)

        raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts.")
