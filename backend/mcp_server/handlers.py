"""Handlers for MCP server endpoints.

Provides:
- similarity_by_text()
- similarity_by_point()

Adds lightweight logging of request flow and processing time.
"""

from typing import Dict, Any, List
import logging
import time

logger = logging.getLogger(__name__)


class Handlers:
    """Encapsulates business logic for similarity search and spatial lookup."""

    def __init__(self, db_client):
        """Initialize handler with a DuckDB client.

        Args:
            db_client: Instance of DuckDBClient.
        """
        self.db = db_client

    # ------------------------------------------------------------------
    # Text Query Similarity
    # ------------------------------------------------------------------
    async def similarity_by_text(self, text: str) -> List[Dict[str, Any]]:
        """Run similarity search by using OSM to resolve text to a location.

        Args:
            text (str): User text query.

        Returns:
            List[Dict[str, Any]]: Results sorted by similarity.
        """
        logger.info(f"[Handlers] similarity_by_text text='{text}'")
        t0 = time.perf_counter()

        # Resolve text → geocode via OSM
        poi = await self._geocode_text(text)
        lon = poi["lon"]
        lat = poi["lat"]

        logger.info(f"[Handlers] OSM resolved to lon={lon}, lat={lat}")

        # Run similarity via spatial lookup
        results = await self.similarity_by_point(lon, lat)

        dt = time.perf_counter() - t0
        logger.info(f"[Handlers] similarity_by_text completed (elapsed={dt:.3f}s)")

        return results

    # ------------------------------------------------------------------
    # Point Similarity
    # ------------------------------------------------------------------
    async def similarity_by_point(self, lon: float, lat: float) -> List[Dict[str, Any]]:
        """Run similarity search by point lookup + vector comparison.

        Args:
            lon (float): Longitude.
            lat (float): Latitude.

        Returns:
            List[Dict[str, Any]]: Similar chips sorted by similarity.
        """
        logger.info(f"[Handlers] similarity_by_point lon={lon}, lat={lat}")
        t0 = time.perf_counter()

        chip = self.db.get_chip_by_point(lon, lat)
        if not chip:
            logger.warning("[Handlers] No chip found for given coordinates")
            return []

        seed_vec = chip["vec"]

        # Run similarity search
        results = self.db.get_similar_chips(seed_vec, limit=12)

        dt = time.perf_counter() - t0
        logger.info(
            f"[Handlers] similarity_by_point returned {len(results)} results "
            f"(elapsed={dt:.3f}s)"
        )

        return results

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------
    async def _geocode_text(self, text: str) -> Dict[str, float]:
        """Resolve natural language text using the OSM geocoding API.

        Args:
            text (str): Query text.

        Returns:
            Dict[str, float]: Coordinates dictionary with keys 'lon' and 'lat'.
        """
        import httpx

        logger.info(f"[Handlers] Geocoding text '{text}'")

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": text,
            "format": "json",
            "limit": 1,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)

        resp.raise_for_status()
        data = resp.json()

        if not data:
            raise ValueError(f"No geocoding results for text: {text}")

        top = data[0]
        lon = float(top["lon"])
        lat = float(top["lat"])

        logger.info(f"[Handlers] Geocoding '{text}' resolved to lon={lon}, lat={lat}")

        return {"lon": lon, "lat": lat}
