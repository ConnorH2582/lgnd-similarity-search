"""OSM/Nominatim geocoding client with fuzzy fallback logic for conceptual queries."""

from typing import Dict, Optional
import httpx
import difflib
import logging
import time

logger = logging.getLogger(__name__)


class OsmClient:
    """Client for querying OSM's Nominatim service or using local fallbacks.

    This layer interprets user queries and produces a (lat, lon) anchor point
    for the similarity-search pipeline. Conceptual queries like "coastal marina"
    or "parking lot" are not literal place names, so fallbacks and fuzzy matching
    ensure robust behavior.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    # Known conceptual categories relevant to the LGND take-home.
    FALLBACKS = {
        "marina": {"lat": 37.8065, "lon": -122.4410},
        "coastal marina": {"lat": 37.8065, "lon": -122.4410},
        "harbor": {"lat": 37.8065, "lon": -122.4410},
        "airport": {"lat": 37.6152, "lon": -122.3899},
        "airplanes": {"lat": 37.6152, "lon": -122.3899},
        "runway": {"lat": 37.6152, "lon": -122.3899},
        "parking": {"lat": 37.7840, "lon": -122.4090},
        "parking lot": {"lat": 37.7840, "lon": -122.4090},
        "downtown": {"lat": 37.7884, "lon": -122.4076},
    }

    def fuzzy_match(self, query: str) -> Optional[str]:
        """Return the closest fallback key using fuzzy matching.

        Args:
            query: The natural-language query string.

        Returns:
            A fallback key if the fuzzy match is strong enough, otherwise None.
        """
        candidates = list(self.FALLBACKS.keys())
        match_start = time.perf_counter()
        matches = difflib.get_close_matches(query, candidates, n=1, cutoff=0.55)
        match_end = time.perf_counter()

        logger.info(
            f"[OsmClient] fuzzy_match('{query}') → {matches if matches else None} "
            f"(elapsed={match_end - match_start:.3f}s)"
        )

        return matches[0] if matches else None

    async def geocode(self, query: str) -> Optional[Dict[str, float]]:
        """Geocode a query using OSM, with fuzzy fallbacks for reliability.

        Args:
            query: Natural-language input.

        Returns:
            A dict with keys {name, lat, lon} or None if nothing can be resolved.
        """
        q = query.lower().strip()
        logger.info(f"[OsmClient] BEGIN geocode('{query}')")

        # --- Step 1: Exact match fallback ---
        if q in self.FALLBACKS:
            coords = self.FALLBACKS[q]
            logger.info(
                f"[OsmClient] Exact fallback match for '{query}' → {coords}"
            )
            return {
                "name": f"Fallback: {query}",
                "lat": coords["lat"],
                "lon": coords["lon"],
            }

        # --- Step 2: Fuzzy match fallback ---
        fuzzy = self.fuzzy_match(q)
        if fuzzy:
            coords = self.FALLBACKS[fuzzy]
            logger.info(
                f"[OsmClient] Fuzzy fallback match for '{query}' → '{fuzzy}' → {coords}"
            )
            return {
                "name": f"Fuzzy fallback: {fuzzy}",
                "lat": coords["lat"],
                "lon": coords["lon"],
            }

        # --- Step 3: Try live OSM geocoding ---
        logger.info(
            f"[OsmClient] No fallback match. Attempting live OSM geocoding for '{query}'..."
        )

        headers = {
            "User-Agent": "LGND-TakeHome/1.0 (contact@localhost)",
            "Accept-Language": "en-US,en;q=0.9",
        }

        params = {
            "q": f"{query} in San Francisco, California, USA",
            "format": "json",
            "limit": 1,
        }

        t0 = time.perf_counter()

        try:
            async with httpx.AsyncClient(headers=headers, timeout=10) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"[OsmClient] OSM request FAILED for '{query}' → {e}")
            return None

        elapsed = time.perf_counter() - t0
        logger.info(
            f"[OsmClient] Live OSM geocoding completed in {elapsed:.3f}s "
            f"→ data: {data if data else 'NONE'}"
        )

        # --- Step 4: Validate OSM result ---
        if not data:
            logger.warning(f"[OsmClient] No OSM results for '{query}'")
            return None

        hit = data[0]
        result = {
            "name": hit.get("display_name", ""),
            "lat": float(hit["lat"]),
            "lon": float(hit["lon"]),
        }

        logger.info(f"[OsmClient] SUCCESS geocode('{query}') → {result}")
        return result
