"""
Application-level handlers coordinating OSM geocoding and DuckDB similarity search.

This version removes all fake-location shortcuts and uses:

    ✔ REAL OSM geocoding (cached)
    ✔ REAL chip spatial lookup (cached)
    ✔ REAL vector similarity (cached)
    ✔ Warmup to make first queries fast

"""

import time
import logging
from typing import Any, Dict, List

from .duckdb_client import DuckDBClient
from .osm_client import OsmClient

logger = logging.getLogger(__name__)

THUMB_BASE = "https://lgnd-fullstack-takehome-thumbnails.s3.us-east-2.amazonaws.com"


class MCPHandlers:
    """Coordinator for real OSM → chip lookup → similarity search with caching."""

    def __init__(self, db_path: str) -> None:
        logger.info(f"[MCPHandlers] Initializing with DB at: {db_path}")

        self.db = DuckDBClient(db_path)
        self.osm = OsmClient()

        # CACHES
        self._geocode_cache = {}   # text query → {"lat":..,"lon":..}
        self._chip_cache = {}      # (lon,lat) key → chip dict
        self._sim_cache = {}       # seed_chip_id → similarity matches list

        logger.info("[MCPHandlers] Caching initialized.")

        # Warm up frequently used queries so demo is instant
        self._warmup_queries = [
            "airport", "marina", "parking lot", "downtown", "bridge"
        ]

        logger.info("[MCPHandlers] Starting warmup...")
        self._warmup()
        logger.info("[MCPHandlers] Warmup complete.")

    # --------------------------------------------------------------
    # Helper: round coords for stable cache keys
    # --------------------------------------------------------------
    def _cache_key(self, lon: float, lat: float):
        return (round(lon, 4), round(lat, 4))

    # --------------------------------------------------------------
    # Warmup logic — runs OSM → spatial lookup → similarity once
    # --------------------------------------------------------------
    def _warmup(self):
        """Perform warmup for a few common queries."""
        for q in self._warmup_queries:
            try:
                logger.info(f"[Warmup] Precomputing for '{q}'")

                # Real OSM lookup (cached)
                poi = self.osm.sync_geocode(q)   # MUST exist in your OsmClient

                if poi:
                    # Chip lookup (cached)
                    key = self._cache_key(poi["lon"], poi["lat"])
                    chip = self.db.get_chip_by_point(poi["lon"], poi["lat"])
                    if chip:
                        self._chip_cache[key] = chip
                        seed_id = chip["chips_id"]

                        # Similarity search (cached)
                        matches = self.db.get_similar_chips(chip["vec"], limit=8)
                        self._sim_cache[seed_id] = matches

                logger.info(f"[Warmup] '{q}' cached successfully.")

            except Exception as e:
                logger.warning(f"[Warmup] Failed precomputing '{q}': {e}")

    # --------------------------------------------------------------
    # REAL similarity by POINT (cached)
    # --------------------------------------------------------------
    async def similarity_by_point(self, lon: float, lat: float) -> Dict[str, Any]:
        logger.info(f"[similarity_by_point] BEGIN lon={lon}, lat={lat}")
        t_start = time.perf_counter()

        key = self._cache_key(lon, lat)

        # 1️⃣ CHIP LOOKUP CACHE
        if key in self._chip_cache:
            chip = self._chip_cache[key]
            logger.info("[similarity_by_point] Chip lookup served from cache.")
        else:
            logger.info("[similarity_by_point] Performing REAL spatial chip lookup...")
            chip = self.db.get_chip_by_point(lon, lat)
            if chip is None:
                logger.warning("[similarity_by_point] No chip found for coordinates.")
                return {"error": "No chip found at that location", "lon": lon, "lat": lat}

            self._chip_cache[key] = chip
            logger.info("[similarity_by_point] Chip cached.")

        seed_chip_id = chip["chips_id"]
        seed_vec = chip["vec"]

        # 2️⃣ SIMILARITY CACHE
        if seed_chip_id in self._sim_cache:
            matches = self._sim_cache[seed_chip_id]
            logger.info("[similarity_by_point] Similarity results served from cache.")
        else:
            logger.info(f"[similarity_by_point] Running REAL vector similarity for seed {seed_chip_id}...")
            sim_start = time.perf_counter()
            matches = self.db.get_similar_chips(seed_vec, limit=8)
            sim_end = time.perf_counter()

            logger.info(
                f"[similarity_by_point] Vector search returned "
                f"{len(matches)} results in {sim_end - sim_start:.3f}s"
            )
            self._sim_cache[seed_chip_id] = matches
            logger.info("[similarity_by_point] Similarity cached.")

        # 3️⃣ Build response payload
        results = []
        for m in matches:
            cid = m["chips_id"]
            results.append({
                **m,
                "thumbnail": f"{THUMB_BASE}/{cid}_native.jpeg"
            })

        logger.info(
            f"[similarity_by_point] END seed={seed_chip_id}, "
            f"latency={time.perf_counter() - t_start:.3f}s"
        )

        return {
            "seed_chip": seed_chip_id,
            "results": results,
        }

    # --------------------------------------------------------------
    # REAL similarity by TEXT (cached)
    # --------------------------------------------------------------
    async def similarity_by_text(self, query: str) -> Dict[str, Any]:
        logger.info(f"[similarity_by_text] BEGIN query='{query}'")
        t_start = time.perf_counter()
        q_lower = query.lower().strip()

        # 1️⃣ REAL OSM GEOCODING (with cache)
        if q_lower in self._geocode_cache:
            poi = self._geocode_cache[q_lower]
            logger.info("[similarity_by_text] Geocode served from cache.")
        else:
            logger.info(f"[similarity_by_text] Resolving '{query}' via REAL OSM...")
            poi = await self.osm.geocode(query)

            if poi is None:
                return {"error": "No OSM result for query", "query": query}

            self._geocode_cache[q_lower] = poi
            logger.info("[similarity_by_text] Geocode cached.")

        # 2️⃣ DELEGATE to the cached similarity_by_point
        logger.info(
            f"[similarity_by_text] Running similarity_by_point for POI ({poi['lon']}, {poi['lat']})"
        )

        similarity_result = await self.similarity_by_point(poi["lon"], poi["lat"])

        logger.info(
            f"[similarity_by_text] END query='{query}', "
            f"pipeline={time.perf_counter() - t_start:.3f}s"
        )

        return {
            "query": query,
            "poi": poi,
            **similarity_result,
        }
