"""Application-level handlers that coordinate OSM geocoding and DuckDB similarity search.

This module defines the MCPHandlers class, which exposes high-level workflows:

1. similarity_by_text()  — user provides a natural-language query
    → OSM geocoder resolves coordinates
    → find chip containing that point
    → vector similarity search
    → return matching imagery tiles

2. similarity_by_point() — user provides explicit lon/lat
    → find chip containing that point
    → similarity search
    → return matches

Timing logs help diagnose where the pipeline is slow (OSM vs DuckDB).
"""

import time
import logging
from typing import Any, Dict

from .duckdb_client import DuckDBClient
from .osm_client import OsmClient

logger = logging.getLogger(__name__)

THUMB_BASE = "https://lgnd-fullstack-takehome-thumbnails.s3.us-east-2.amazonaws.com"


class MCPHandlers:
    """Coordinator for OSM-based geocoding and DuckDB similarity search.

    Acts as the glue between external services (OSM), the embeddings database
    (DuckDB), and the FastAPI routes that surface the results.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize handler dependencies.

        Args:
            db_path (str): Path to the DuckDB `embeddings.db` file.
        """
        logger.info(f"[MCPHandlers] Initializing with DB at: {db_path}")
        self.db = DuckDBClient(db_path)
        self.osm = OsmClient()
        logger.info("[MCPHandlers] Initialization complete.")

    # ----------------------------------------------------------------------
    # Similarity by POINT
    # ----------------------------------------------------------------------
    async def similarity_by_point(self, lon: float, lat: float) -> Dict[str, Any]:
        """Run a similarity search anchored at a specific geographic point.

        Steps:
            1. Find the embedding chip whose polygon contains (lon, lat)
            2. Extract its vector
            3. Run cosine similarity search across all 567k chips
            4. Return the top-N similar results

        Args:
            lon (float): Longitude in WGS84.
            lat (float): Latitude in WGS84.

        Returns:
            Dict[str, Any]: Payload with seed chip, results, and thumbnails.
        """
        logger.info(f"[similarity_by_point] BEGIN lon={lon}, lat={lat}")
        t_start = time.perf_counter()

        # --- Step 1: spatial lookup ---
        chip_lookup_start = time.perf_counter()
        logger.info("[similarity_by_point] Performing spatial chip lookup...")
        chip = self.db.get_chip_by_point(lon, lat)
        chip_lookup_end = time.perf_counter()

        logger.info(
            f"[similarity_by_point] Spatial lookup completed in "
            f"{chip_lookup_end - chip_lookup_start:.3f}s"
        )

        if chip is None:
            logger.warning(
                f"[similarity_by_point] No chip found at ({lon}, {lat})"
            )
            return {"error": "No chip found at that location", "lon": lon, "lat": lat}

        seed_chip_id = chip["chips_id"]
        seed_vec = chip["vec"]

        # --- Step 2: Similarity search ---
        logger.info(
            f"[similarity_by_point] Running vector similarity search for seed chip {seed_chip_id}"
        )
        sim_start = time.perf_counter()
        matches = self.db.get_similar_chips(seed_vec, limit=8)
        sim_end = time.perf_counter()

        logger.info(
            f"[similarity_by_point] Vector similarity search returned {len(matches)} results "
            f"in {sim_end - sim_start:.3f}s"
        )

        # --- Step 3: Build response payload ---
        results = []
        for m in matches:
            chip_id = m["chips_id"]
            thumb_url = f"{THUMB_BASE}/{chip_id}_native.jpeg"

            logger.debug(
                f"[similarity_by_point] Adding match chip {chip_id} with thumbnail {thumb_url}"
            )

            results.append(
                {
                    **m,
                    "thumbnail": thumb_url,
                }
            )

        total = time.perf_counter() - t_start
        logger.info(
            f"[similarity_by_point] END for seed chip {seed_chip_id} "
            f"(total latency={total:.3f}s)"
        )

        return {
            "seed_chip": seed_chip_id,
            "results": results,
        }

    # ----------------------------------------------------------------------
    # Similarity by TEXT (full pipeline)
    # ----------------------------------------------------------------------
    async def similarity_by_text(self, query: str) -> Dict[str, Any]:
        """Run a full similarity workflow from natural-language text.

        Steps:
            1. Resolve text → lat/lon with OSM
            2. Run similarity_by_point(lon, lat)

        Args:
            query (str): User text query such as "marina", "airport", "parking lot".

        Returns:
            Dict[str, Any]: Combined result containing OSM POI + similarity matches.
        """
        logger.info(f"[similarity_by_text] BEGIN query='{query}'")
        t_start = time.perf_counter()

        # --- Step 1: OSM Geocoding ---
        logger.info(
            f"[similarity_by_text] Resolving query '{query}' via OSM/fallback logic..."
        )
        osm_start = time.perf_counter()
        poi = await self.osm.geocode(query)
        osm_end = time.perf_counter()

        logger.info(
            f"[similarity_by_text] OSM resolved query '{query}' in "
            f"{osm_end - osm_start:.3f}s → result: {poi}"
        )

        if poi is None:
            logger.warning(
                f"[similarity_by_text] No OSM resolution for query='{query}'"
            )
            return {"error": "No OSM result for query", "query": query}

        # --- Step 2: Similarity by point ---
        logger.info(
            f"[similarity_by_text] Running similarity_by_point({poi['lon']}, {poi['lat']})"
        )
        sim_start = time.perf_counter()
        similarity_result = await self.similarity_by_point(poi["lon"], poi["lat"])
        sim_end = time.perf_counter()

        logger.info(
            f"[similarity_by_text] similarity_by_point completed in "
            f"{sim_end - sim_start:.3f}s"
        )

        total = time.perf_counter() - t_start
        logger.info(
            f"[similarity_by_text] END query='{query}' "
            f"(total pipeline={total:.3f}s)"
        )

        return {
            "query": query,
            "poi": poi,
            **similarity_result,
        }
