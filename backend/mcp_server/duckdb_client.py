"""DuckDB client for vector and spatial operations over LGND embeddings.

Handles:
- Spatial lookup: find chip whose geometry contains a lon/lat point
- Vector similarity search: cosine similarity against 1024-dim embedding vectors
- Metadata lookup: chip centroid for display

All queries are logged with timing instrumentation for performance analysis.
"""

from typing import List, Dict, Any, Optional
import duckdb
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)


class DuckDBClient:
    """Client for interacting with the `embeddings` DuckDB database."""

    def __init__(self, db_path: str = None) -> None:
        """
        Create a DuckDB connection and load spatial extension.
        If db_path is not provided, it resolves the correct absolute
        path to the project's root-level embeddings.db file.
        """

        import os

        # Determine project root (two levels above this file)
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        # If user didn’t supply a db_path, use the root-level embeddings.db
        if db_path is None:
            db_path = os.path.join(project_root, "embeddings.db")

        self.db_path = db_path
        logger.info(f"[DuckDBClient] Connecting to DuckDB at {db_path}")
        print(">>> ABSOLUTE DB PATH:", db_path)
        print(">>> EXISTS:", os.path.exists(db_path))

        # Connect
        self.con = duckdb.connect(db_path)

        self._load_extensions()

    def _load_extensions(self) -> None:
        """Install and load DuckDB spatial extension if needed."""
        try:
            logger.info("[DuckDBClient] Installing spatial extension...")
            self.con.execute("INSTALL spatial;")
        except Exception:
            logger.info("[DuckDBClient] Spatial extension already installed.")

        self.con.execute("LOAD spatial;")
        logger.info("[DuckDBClient] Spatial extension loaded.")

    def get_chip_by_point(self, lon: float, lat: float) -> Optional[Dict[str, Any]]:
        """Return chip metadata for the tile containing (lon, lat).

        Args:
            lon (float): Longitude
            lat (float): Latitude

        Returns:
            Optional[Dict[str, Any]]: containing:
                - chips_id (str)
                - vec (List[float]): 1024-dim embedding
            or None if the point is not inside any geom polygon.
        """
        logger.info(f"[DuckDBClient] Spatial query for lon={lon}, lat={lat}")
        t0 = time.perf_counter()

        query = """
            SELECT chips_id, vec
            FROM embeddings
            WHERE ST_Contains(geom, ST_Point(?, ?))
            LIMIT 1;
        """

        row = self.con.execute(query, [lon, lat]).fetchone()
        dt = time.perf_counter() - t0

        if not row:
            logger.warning(
                f"[DuckDBClient] No chip found at lon={lon}, lat={lat} (took {dt:.3f}s)"
            )
            return None

        chips_id, vec = row
        logger.info(
            f"[DuckDBClient] Found chip '{chips_id}' via spatial lookup in {dt:.3f}s"
        )
        return {"chips_id": chips_id, "vec": vec}

    def get_similar_chips(
        self, seed_vec: List[float], limit: int = 12
    ) -> List[Dict[str, Any]]:
        """Perform cosine similarity search.

        Steps:
            1. Normalize the seed vector (FLOAT32)
            2. Use array_cosine_similarity over the whole embeddings table
            3. Retrieve centroid coordinates for each chip

        Args:
            seed_vec (List[float]): 1024-dim embedding vector.
            limit (int): Number of results to return.

        Returns:
            List[Dict[str, Any]]: list of match dicts with:
                - chips_id
                - similarity
                - lon, lat (centroid)
        """
        logger.info(
            f"[DuckDBClient] Running similarity search (top {limit})"
        )
        t0 = time.perf_counter()

        # Cast vector to float32 and normalize
        seed_vec = np.array(seed_vec, dtype=np.float32)
        if seed_vec.shape[0] != 1024:
            raise ValueError(
                f"Expected seed_vec of length 1024, got {seed_vec.shape[0]}"
            )

        norm = np.linalg.norm(seed_vec)
        if norm == 0:
            raise ValueError("Seed embedding vector has zero magnitude.")

        seed_vec = (seed_vec / norm).tolist()

        query = f"""
            SELECT
                chips_id,
                array_cosine_similarity(vec, CAST(? AS FLOAT[1024])) AS similarity,
                ST_X(ST_Centroid(geom)) AS lon,
                ST_Y(ST_Centroid(geom)) AS lat
            FROM embeddings
            ORDER BY similarity DESC
            LIMIT {limit};
        """

        rows = self.con.execute(query, [seed_vec]).fetchall()
        dt = time.perf_counter() - t0

        logger.info(
            f"[DuckDBClient] Similarity query returned {len(rows)} rows in {dt:.3f}s"
        )

        results: List[Dict[str, Any]] = []
        for chips_id, sim, lon, lat in rows:
            results.append(
                {
                    "chips_id": chips_id,
                    "similarity": float(sim),
                    "lon": float(lon),
                    "lat": float(lat),
                }
            )

        return results

    # ----------------------------------------------------------------------
    # Metadata
    # ----------------------------------------------------------------------
    def get_chip_metadata(self, chips_id: str) -> Optional[Dict[str, Any]]:
        """Fetch centroid metadata for a chip.

        Args:
            chips_id (str): Embedding chip identifier.

        Returns:
            Optional[Dict[str, Any]]: A dictionary with:
                - "chips_id" (str)
                - "lon" (float)
                - "lat" (float)
            Returns None if no chip exists with that ID.
        """
        query = """
            SELECT chips_id,
                   ST_X(ST_Centroid(geom)) AS lon,
                   ST_Y(ST_Centroid(geom)) AS lat
            FROM embeddings
            WHERE chips_id = ?
            LIMIT 1;
        """

        row = self.con.execute(query, [chips_id]).fetchone()
        if not row:
            return None

        chips_id, lon, lat = row
        return {"chips_id": chips_id, "lon": lon, "lat": lat}
