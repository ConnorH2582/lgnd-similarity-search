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
        logger.info(f"Initializing MCPHandlers with DB at: {db_path}")
        self.db = DuckDBClient(db_path)
        self.osm = OsmClient()

    async def similarity_by_point(self, lon: float, lat: float) -> Dict[str, Any]:
        """Run a similarity search anchored at a specific geographic point.

        Steps:
            1. Find the embedding chip whose polygon contains (lon, lat)
            2. Extract its vector
            3. Run cosine similarity search across all 567k chips
            4. Return the top-N similar results

        Timing instrumentation added to identify slow steps.

        Args:
            lon (float): Longitude in WGS84.
            lat (float): Latitude in WGS84.

        Returns:
            Dict[str, Any]: Results including:
                - seed_chip (str)
                - results (list of chip matches)
                - thumbnail URLs
            Or an error dict if no chip is found.
        """
        logger.info(f"[similarity_by_point] Starting search at lon={lon}, lat={lat}")
        t_start = time.perf_counter()

        # --- Step 1: spatial lookup ---
        chip_lookup_start = time.perf_counter()
        chip = self.db.get_chip_by_point(lon, lat)
        chip_lookup_end = time.perf_counter()

        logger.info(
            f"[similarity_by_point] Spatial lookup took "
            f"{chip_lookup_end - chip_lookup_start:.3f}s"
        )

        if chip is None:
            logger.warning(
                f"[similarity_by_point] No chip found for lon={lon}, lat={lat}"
            )
            return {"error": "No chip found at that location", "lon": lon, "lat": lat}

        seed_chip_id = chip["chips_id"]
        seed_vec = chip["vec"]

        # --- Step 2: Similarity search ---
        sim_start = time.perf_counter()
        matches = self.db.get_similar_chips(seed_vec, limit=8)
        sim_end = time.perf_counter()
        logger.info(
            f"[similarity_by_point] Vector similarity search took {sim_end - sim_start:.3f}s"
        )

        # --- Step 3: Build return payload ---
        results = []
        for m in matches:
            chip_id = m["chips_id"]
            thumb_url = f"{THUMB_BASE}/{chip_id}_native.jpeg"
            results.append(
                {
                    **m,
                    "thumbnail": thumb_url,
                }
            )

        t_total = time.perf_counter() - t_start
        logger.info(
            f"[similarity_by_point] Total end-to-end latency: {t_total:.3f}s for seed chip {seed_chip_id}"
        )

        return {
            "seed_chip": seed_chip_id,
            "results": results,
        }

    async def similarity_by_text(self, query: str) -> Dict[str, Any]:
        """Run a full similarity workflow from natural-language text.

        Steps:
            1. Resolve text → lat/lon with OSM
            2. Run similarity_by_point(lon, lat)

        This is the main entrypoint used by the frontend.

        Args:
            query (str): e.g. "coastal marina", "airport", "parking lot".

        Returns:
            Dict[str, Any]: Including:
                - query
                - anchor POI
                - similarity results
            Or an error dict if the query cannot be resolved by OSM.
        """
        logger.info(f"[similarity_by_text] Starting OSM lookup for query='{query}'")
        t_start = time.perf_counter()

        # --- Step 1: OSM geocoding ---
        osm_start = time.perf_counter()
        poi = await self.osm.geocode(query)
        osm_end = time.perf_counter()

        logger.info(
            f"[similarity_by_text] OSM geocoding took {osm_end - osm_start:.3f}s "
            f"for query='{query}'"
        )

        if poi is None:
            logger.warning(
                f"[similarity_by_text] No OSM result for query='{query}'"
            )
            return {"error": "No OSM result for query", "query": query}

        # --- Step 2: similarity search ---
        sim_start = time.perf_counter()
        similarity_result = await self.similarity_by_point(poi["lon"], poi["lat"])
        sim_end = time.perf_counter()

        logger.info(
            f"[similarity_by_text] similarity_by_point() took {sim_end - sim_start:.3f}s"
        )

        t_total = time.perf_counter() - t_start
        logger.info(
            f"[similarity_by_text] Full text→OSM→similarity pipeline took {t_total:.3f}s"
        )

        return {
            "query": query,
            "poi": poi,
            **similarity_result,
        }